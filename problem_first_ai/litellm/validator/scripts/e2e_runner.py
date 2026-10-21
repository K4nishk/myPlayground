#!/usr/bin/env python3
"""End-to-end validator for the local model gateway.

Reads the gateway config (which alias maps to which backend model) and a cases file, probes
every backend and the gateway, loads each alias's model and makes an opening call, sends each
case to its alias, and reports pass or fail with load time, latency, tokens per second and
memory. Exit code 0 when every case passes, 1 otherwise.

Paths default to the gateway folder (problem_first_ai/litellm/), so it runs from anywhere:

    uv run --frozen --project problem_first_ai/litellm \\
        python problem_first_ai/litellm/validator/scripts/e2e_runner.py          # table
    ... e2e_runner.py --json                                                     # report
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from openai import APIConnectionError, APIStatusError, OpenAI

VALIDATOR_DIR = Path(__file__).resolve().parent.parent
GATEWAY_DIR = VALIDATOR_DIR.parent
GiB = 2**30
# The gateway names the backend model it actually sent a call to in this response header.
ROUTED_HEADER = "x-litellm-model-name"
OPENING_PROMPT = "Reply with the single word OK."
OPENING_BUDGET = 16
# Seconds to wait after unloading before the timed load. Measured on Ollama 0.40.6: a load within
# 2 s of an unload took 5.1-6.4 s, one 5 s or more later took 0.8 s (2026-10-21 baseline note).
UNLOAD_SETTLE_S = 5.0
# Errors from a backend's own HTTP API (urllib's URLError is an OSError).
BACKEND_ERRORS = (OSError, ValueError, KeyError)
# Run-level failures; the blocking ones leave nothing worth testing, so no case is sent after them.
BLOCKING_FAILURES = frozenset({"backend_unhealthy", "gateway_unreachable", "gateway_rejected_key", "gateway_error"})
RUN_FAILURES = BLOCKING_FAILURES | {"alias_mismatch", "misroute"}
CASE_FAILURES = frozenset({"error", "misroute", "budget_exhausted", "empty_answer", "check_failed"})
WARNINGS = frozenset({"swap", "swap_unknown", "context_mismatch"})
ALIAS_SETTINGS = frozenset({"temperature"})
NUMBER = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
THINK = re.compile(r"<think>(.*?)(?:</think>|$)", re.DOTALL)


class ConfigError(Exception):
    """The gateway config or the cases file can't be used."""


# --- inputs -----------------------------------------------------------------------------

@dataclass(frozen=True)
class Alias:
    name: str
    prefix: str          # LiteLLM's route prefix in litellm_params.model, e.g. "ollama_chat"
    backend_model: str   # the model the backend serves, e.g. "deepseek-r1:14b"
    api_base: str
    num_ctx: int | None  # the context window the config asks for, if it sets one
    temperature: float | None = 0  # sent with every call to the alias; None sends none (alias_settings)

    @property
    def route(self) -> str:
        return f"{self.prefix}/{self.backend_model}"


@dataclass(frozen=True)
class Case:
    id: str
    alias: str
    api: str
    prompt: str
    output_budget: int
    checks: list[dict] = field(default_factory=list)
    reasoning_effort: str | None = None  # sent the way the course's ChatOpenAI sends it


def load_aliases(path: str | Path) -> dict[str, Alias]:
    config = yaml.safe_load(Path(path).read_text()) or {}
    aliases = {}
    for entry in config.get("model_list") or []:
        params = entry.get("litellm_params") or {}
        prefix, _, backend_model = str(params.get("model", "")).partition("/")
        if not entry.get("model_name") or not backend_model:
            raise ConfigError(f"{path}: every model_list entry needs model_name and a prefixed litellm_params.model")
        num_ctx = int(params["num_ctx"]) if params.get("num_ctx") else None
        aliases[entry["model_name"]] = Alias(entry["model_name"], prefix, backend_model,
                                             str(params.get("api_base", "")).rstrip("/"), num_ctx)
    if not aliases:
        raise ConfigError(f"{path}: model_list defines no aliases")
    return aliases


def load_alias_settings(path: str | Path, aliases: dict[str, Alias]) -> dict[str, Alias]:
    """Apply the cases file's alias_settings, which say how the runner calls an alias."""
    data = yaml.safe_load(Path(path).read_text()) or {}
    settings = data.get("alias_settings") or {}
    if not isinstance(settings, dict):
        raise ConfigError(f"{path}: alias_settings must map aliases to their settings")
    aliases = dict(aliases)
    for name, values in settings.items():
        if name not in aliases:
            raise ConfigError(f"{path}: alias_settings names {name!r}, which is not in the gateway config")
        if not isinstance(values, dict):
            raise ConfigError(f"{path}: alias_settings for {name!r} must be a mapping")
        if unknown := sorted(set(values) - ALIAS_SETTINGS):
            raise ConfigError(f"{path}: alias_settings for {name!r} has unknown setting(s) {unknown}; "
                              f"known: {sorted(ALIAS_SETTINGS)}")
        temperature = values.get("temperature", 0)
        if temperature is not None and not isinstance(temperature, (int, float)):
            raise ConfigError(f"{path}: alias_settings for {name!r}: temperature must be a number or null")
        aliases[name] = replace(aliases[name], **values)
    return aliases


def load_cases(path: str | Path, aliases: dict[str, Alias]) -> list[Case]:
    data = yaml.safe_load(Path(path).read_text()) or {}
    cases = []
    for item in data.get("cases") or []:
        try:
            # A case may name several aliases: it runs once for each, so they answer the same prompt
            # under the same checks.
            names = item["alias"] if isinstance(item["alias"], list) else [item["alias"]]
            expanded = [Case(id=str(item["id"]), alias=str(name), api=item.get("api", "chat"), prompt=item["prompt"],
                             output_budget=int(item["output_budget"]), checks=item.get("checks") or [],
                             reasoning_effort=item.get("reasoning_effort")) for name in names]
        except (KeyError, TypeError, ValueError) as exc:
            raise ConfigError(f"case {item.get('id', '?')!r}: missing or invalid field ({exc})") from exc
        if not expanded:
            raise ConfigError(f"case {item.get('id', '?')!r}: needs at least one alias")
        for case in expanded:
            if case.alias not in aliases:
                raise ConfigError(f"case {case.id!r}: alias {case.alias!r} is not in the gateway config")
            if case.api not in CALLS:
                raise ConfigError(f"case {case.id!r}: api must be one of {sorted(CALLS)}")
            if not case.checks:
                raise ConfigError(f"case {case.id!r}: needs at least one check")
            for check in case.checks:
                if check.get("type") not in CHECKS or "expected" not in check:
                    raise ConfigError(f"case {case.id!r}: each check needs a type from {sorted(CHECKS)} "
                                      "and an expected value")
            cases.append(case)
    # A run covers every alias the gateway serves, so each one needs at least one case.
    uncovered = sorted(set(aliases) - {c.alias for c in cases})
    if uncovered:
        raise ConfigError(f"{path}: no cases for alias(es) {uncovered}")
    return cases


# --- backends and gateway ---------------------------------------------------------------

def http_json(method: str, url: str, body: dict | None = None, timeout: float = 10) -> Any:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        text = resp.read().decode()
    return json.loads(text) if text.strip() else None


class OllamaBackend:
    """Ollama's own API, beside the OpenAI-compatible one the gateway uses."""

    kind = "ollama"

    def __init__(self, api_base: str):
        self.api_base = api_base

    @staticmethod
    def _tag(model: str) -> str:
        # Ollama reports an untagged model as name:latest.
        return model if ":" in model else f"{model}:latest"

    def version(self) -> str:
        return http_json("GET", f"{self.api_base}/api/version")["version"]

    def resident(self) -> dict[str, dict]:
        """Each loaded model's memory, GPU share and context window, keyed by model tag."""
        models = http_json("GET", f"{self.api_base}/api/ps").get("models") or []
        return {self._tag(m.get("name") or m.get("model") or ""): {
                    "resident_gib": round(m.get("size", 0) / GiB, 2),
                    "gpu_gib": round(m.get("size_vram", 0) / GiB, 2),
                    "context_length": m.get("context_length"),
                } for m in models}

    def footprint(self, model: str) -> dict | None:
        """The model's entry from resident(), or None when it isn't loaded."""
        return self.resident().get(self._tag(model))

    def load(self, model: str) -> float:
        """Load the model without generating anything; returns the seconds it took.

        Ollama's load-only reply carries no load_duration, so the request itself is timed.
        """
        started = time.monotonic()
        http_json("POST", f"{self.api_base}/api/generate", {"model": model}, timeout=600)
        return time.monotonic() - started

    def unload(self, model: str) -> None:
        http_json("POST", f"{self.api_base}/api/generate", {"model": model, "keep_alive": 0}, timeout=60)


BACKENDS = {"ollama_chat": OllamaBackend, "ollama": OllamaBackend}


def backend_for(alias: Alias) -> OllamaBackend | None:
    backend_class = BACKENDS.get(alias.prefix)
    return backend_class(alias.api_base) if backend_class else None


def failure(kind: str, detail: str) -> dict:
    assert kind in RUN_FAILURES, kind
    return {"kind": kind, "detail": detail}


def warning(kind: str, detail: str) -> dict:
    assert kind in WARNINGS, kind
    return {"kind": kind, "detail": detail}


def probe_backends(aliases: dict[str, Alias]) -> list[dict]:
    results = []
    for api_base in sorted({a.api_base for a in aliases.values()}):
        backend = backend_for(next(a for a in aliases.values() if a.api_base == api_base))
        entry = {"api_base": api_base, "kind": backend.kind if backend else "unknown",
                 "healthy": None, "version": None, "error": None}
        if backend:
            try:
                entry.update(version=backend.version(), healthy=True)
            except BACKEND_ERRORS as exc:
                entry.update(healthy=False, error=f"{type(exc).__name__}: {exc}")
        results.append(entry)
    return results


def probe_gateway(url: str, client: OpenAI) -> tuple[dict, dict | None]:
    """Liveness, then the alias list. Returns the gateway entry and a run-level failure, if any."""
    entry = {"url": url, "alive": False, "aliases": []}
    try:
        http_json("GET", f"{url}/health/liveliness")
    except BACKEND_ERRORS as exc:
        return entry, failure("gateway_unreachable", f"{url}/health/liveliness: {type(exc).__name__}: {exc}")
    entry["alive"] = True
    try:
        entry["aliases"] = sorted(m.id for m in client.models.list().data)
    except APIStatusError as exc:
        # Without a database, LiteLLM answers a key that isn't the master key with 400 "No connected db.".
        kind = "gateway_rejected_key" if exc.status_code in (400, 401, 403) else "gateway_error"
        return entry, failure(kind, f"/v1/models returned {exc.status_code}: {exc.message}")
    except APIConnectionError as exc:
        return entry, failure("gateway_unreachable", f"/v1/models: {exc}")
    return entry, None


def alias_mismatch(aliases: dict[str, Alias], served: list[str]) -> dict | None:
    missing = sorted(set(aliases) - set(served))
    unexpected = sorted(set(served) - set(aliases))
    if not (missing or unexpected):
        return None
    return failure("alias_mismatch", f"missing from the gateway: {missing or 'none'}; "
                                     f"served but not in the config: {unexpected or 'none'}")


# --- one call ---------------------------------------------------------------------------

def call_chat(client: OpenAI, alias: str, prompt: str, budget: int, reasoning_effort: str | None = None,
              temperature: float | None = 0) -> dict:
    extra = {"reasoning_effort": reasoning_effort} if reasoning_effort else {}
    if temperature is not None:
        extra["temperature"] = temperature
    started = time.monotonic()
    raw = client.chat.completions.with_raw_response.create(
        model=alias, messages=[{"role": "user", "content": prompt}], max_tokens=budget, **extra)
    latency = time.monotonic() - started
    response = raw.parse()
    choice = response.choices[0]
    # LiteLLM moves Ollama's thinking into reasoning_content, outside the typed fields.
    reasoning = (getattr(choice.message, "reasoning_content", None)
                 or (choice.message.model_extra or {}).get("reasoning_content"))
    return {
        "latency_s": latency,
        "answer": choice.message.content or "",
        "reasoning": reasoning or "",
        "finish": choice.finish_reason,
        "output_tokens": response.usage.completion_tokens if response.usage else None,
        "routed_model": raw.headers.get(ROUTED_HEADER),
    }


def call_responses(client: OpenAI, alias: str, prompt: str, budget: int, reasoning_effort: str | None = None,
                   temperature: float | None = 0) -> dict:
    extra = {"reasoning": {"effort": reasoning_effort}} if reasoning_effort else {}
    if temperature is not None:
        extra["temperature"] = temperature
    started = time.monotonic()
    raw = client.responses.with_raw_response.create(
        model=alias, input=prompt, max_output_tokens=budget, **extra)
    latency = time.monotonic() - started
    response = raw.parse()
    reasoning = "".join(part.text or "" for item in response.output if item.type == "reasoning"
                        for part in (item.content or []))
    incomplete = response.incomplete_details.reason if response.incomplete_details else None
    return {
        "latency_s": latency,
        "answer": response.output_text or "",
        "reasoning": reasoning,
        # Report the Responses API's way of saying "out of budget" the way chat says it.
        "finish": "length" if incomplete == "max_output_tokens" else response.status,
        "output_tokens": response.usage.output_tokens if response.usage else None,
        "routed_model": raw.headers.get(ROUTED_HEADER),
    }


CALLS: dict[str, Callable[..., dict]] = {"chat": call_chat, "responses": call_responses}


def split_thinking(text: str) -> tuple[str, str]:
    """Separate inline <think>…</think> reasoning from the answer; an unclosed tag runs to the end."""
    thinking = "".join(THINK.findall(text))
    return THINK.sub("", text).replace("</think>", ""), thinking


# --- checks -----------------------------------------------------------------------------

def final_number(answer: str) -> float | None:
    """The answer's final number: the last \\boxed{} value if there is one, else the last number."""
    boxed = re.findall(r"\\boxed\{([^}]*)\}", answer)
    for text in ([boxed[-1]] if boxed else []) + [answer]:
        numbers = NUMBER.findall(text)
        if numbers:
            return float(numbers[-1].replace(",", ""))
    return None


def check_exact_numeric(expected: Any, answer: str) -> tuple[bool, str]:
    got = final_number(answer)
    return got is not None and abs(got - float(expected)) < 1e-9, f"expected {expected}, got {got}"


def check_contains(expected: Any, answer: str) -> tuple[bool, str]:
    wanted = expected if isinstance(expected, list) else [expected]
    return any(str(w).lower() in answer.lower() for w in wanted), f"expected one of {wanted}"


# Named after the course dataset's answer_check_type values.
CHECKS: dict[str, Callable[[Any, str], tuple[bool, str]]] = {
    "exact_numeric": check_exact_numeric,
    "contains": check_contains,
}


# --- memory -----------------------------------------------------------------------------

def read_memory() -> dict | None:
    """Swap-outs since boot and readily available memory from macOS vm_stat, or None elsewhere.

    E2E_RUNNER_VM_STAT replaces the command (the tests use it to fake swapping).
    """
    command = os.environ.get("E2E_RUNNER_VM_STAT", "vm_stat").split()
    try:
        text = subprocess.run(command, capture_output=True, text=True, timeout=10, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    page = re.search(r"page size of (\d+)", text)
    counts = {k: int(v) for k, v in
              re.findall(r"^(Pages free|Pages inactive|Pages speculative|Swapouts):\s+(\d+)", text, re.M)}
    if not page or "Swapouts" not in counts:
        return None
    available = sum(counts.get(k, 0) for k in ("Pages free", "Pages inactive", "Pages speculative"))
    return {"swapouts": counts["Swapouts"], "available_gib": round(available * int(page.group(1)) / GiB, 1)}


def memory_section(before: dict | None, after: dict | None) -> dict:
    if not (before and after):
        return {"swapouts_delta": None, "available_gib_before": None, "available_gib_after": None}
    return {"swapouts_delta": after["swapouts"] - before["swapouts"],
            "available_gib_before": before["available_gib"], "available_gib_after": after["available_gib"]}


# --- the run ----------------------------------------------------------------------------

def alias_row(alias: Alias) -> dict:
    return {"alias": alias.name, "backend_model": alias.backend_model, "route": alias.route,
            "api_base": alias.api_base, "temperature": alias.temperature,
            "loaded_before_run": None, "unload_settle_s": None,
            "cold": None, "load_s": None,
            "opening_call_s": None, "misroute": None,
            "resident_gib": None, "gpu_gib": None, "context_length": None, "error": None}


def open_alias(client: OpenAI, alias: Alias, backend: OllamaBackend | None, args: argparse.Namespace,
               row: dict) -> None:
    """Load the alias's model on its backend (timed as load_s), then make the opening call through the gateway.

    The load is skipped for backends that can't report what is resident (a frontier API), since a load
    can't be told from a warm call there. The opening call still runs, so connection setup stays out of
    the first case's latency.
    """
    try:
        if backend is not None:
            row["loaded_before_run"] = backend.footprint(alias.backend_model) is not None
            if row["loaded_before_run"] and not args.keep_resident:
                backend.unload(alias.backend_model)
                time.sleep(args.unload_settle)
                row["unload_settle_s"] = args.unload_settle
            row["cold"] = backend.footprint(alias.backend_model) is None
            if row["cold"]:
                row["load_s"] = round(backend.load(alias.backend_model), 2)
        reply = call_chat(client, alias.name, OPENING_PROMPT, OPENING_BUDGET, temperature=alias.temperature)
        row["opening_call_s"] = round(reply["latency_s"], 2)
        row["misroute"] = find_misroute(alias, backend, reply["routed_model"])
        if backend is not None:
            row.update(backend.footprint(alias.backend_model) or {})
    except Exception as exc:  # the cases that follow show the same problem in detail
        row["error"] = f"{type(exc).__name__}: {exc}"


def find_misroute(alias: Alias, backend: OllamaBackend | None, routed_model: str | None) -> str | None:
    """Why the call wasn't served by the alias's backend model, or None if it was."""
    if routed_model and routed_model != alias.route:
        return f"gateway sent {alias.name} to {routed_model}, expected {alias.route}"
    if backend is not None and backend.footprint(alias.backend_model) is None:
        return (f"{alias.backend_model} is not resident on {alias.api_base} "
                f"(resident: {sorted(backend.resident()) or 'none'})")
    return None


def fail_case(result: dict, kind: str, detail: str) -> dict:
    assert kind in CASE_FAILURES, kind
    result.update(failure=kind, detail=detail)
    return result


def run_case(client: OpenAI, case: Case, alias: Alias, backend: OllamaBackend | None) -> dict:
    result = {"id": case.id, "alias": case.alias, "api": case.api, "temperature": alias.temperature,
              "status": "fail", "failure": None,
              "detail": None, "latency_s": None, "output_tokens": None, "tokens_per_s": None,
              "finish": None, "answer_preview": None, "reasoning_chars": None, "routed_model": None}
    try:
        reply = CALLS[case.api](client, case.alias, case.prompt, case.output_budget, case.reasoning_effort,
                                alias.temperature)
    except Exception as exc:
        return fail_case(result, "error", f"{type(exc).__name__}: {exc}")
    answer, inline_thinking = split_thinking(reply["answer"])
    answer = answer.strip()
    result.update(latency_s=round(reply["latency_s"], 2), output_tokens=reply["output_tokens"],
                  finish=reply["finish"], answer_preview=preview(answer),
                  reasoning_chars=len(reply["reasoning"]) + len(inline_thinking),
                  routed_model=reply["routed_model"])
    if reply["output_tokens"] and reply["latency_s"] > 0:
        result["tokens_per_s"] = round(reply["output_tokens"] / reply["latency_s"], 1)
    # A misrouted answer says nothing about this alias, so it outranks every other failure.
    try:
        misroute = find_misroute(alias, backend, reply["routed_model"])
    except BACKEND_ERRORS as exc:
        misroute = f"couldn't ask the backend what is resident: {type(exc).__name__}: {exc}"
    if misroute:
        return fail_case(result, "misroute", misroute)
    # Stopping at the budget means the answer is unfinished, whatever it says so far.
    if reply["finish"] == "length":
        return fail_case(result, "budget_exhausted",
                         f"stopped at the {case.output_budget}-token output budget before finishing")
    if not answer:
        return fail_case(result, "empty_answer", "the model returned no final answer")
    for check in case.checks:
        ok, detail = CHECKS[check["type"]](check["expected"], answer)
        if not ok:
            return fail_case(result, "check_failed", f"{check['type']}: {detail}")
    result["status"] = "pass"
    return result


def preview(text: str, width: int = 60) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= width else "…" + flat[-(width - 1):]


def run(args: argparse.Namespace, aliases: dict[str, Alias], cases: list[Case]) -> dict:
    started_at = datetime.now().astimezone()
    t0 = time.monotonic()
    client = OpenAI(base_url=f"{args.gateway}/v1", api_key=args.api_key, max_retries=0, timeout=args.timeout)
    report = {"started_at": started_at.isoformat(timespec="seconds"), "passed": False,
              "config": str(args.config), "cases_file": str(args.cases),
              "failures": [], "warnings": [], "backends": probe_backends(aliases),
              # Every run records which backend model each alias meant (ADR 0002), even if it stops early.
              "gateway": None, "aliases": [alias_row(a) for a in aliases.values()], "cases": []}
    failures, warnings = report["failures"], report["warnings"]
    failures += [failure("backend_unhealthy", f"{b['kind']} at {b['api_base']}: {b['error']}")
                 for b in report["backends"] if b["healthy"] is False]
    report["gateway"], gateway_failure = probe_gateway(args.gateway, client)
    if gateway_failure:
        failures.append(gateway_failure)
    elif mismatch := alias_mismatch(aliases, report["gateway"]["aliases"]):
        failures.append(mismatch)

    memory_before = read_memory()
    if not any(f["kind"] in BLOCKING_FAILURES for f in failures):
        rows = {row["alias"]: row for row in report["aliases"]}
        served = report["gateway"]["aliases"]
        # One alias at a time: with one model resident at a time, interleaving would reload models.
        for name in dict.fromkeys(c.alias for c in cases if c.alias in served):
            alias, backend, row = aliases[name], backend_for(aliases[name]), rows[name]
            open_alias(client, alias, backend, args, row)
            if row["misroute"]:
                failures.append(failure("misroute", f"{name} opening call: {row['misroute']}"))
            if alias.num_ctx and row["context_length"] and row["context_length"] != alias.num_ctx:
                warnings.append(warning("context_mismatch", (
                    f"{name}: the backend runs a {row['context_length']}-token context window, "
                    f"the config asks for {alias.num_ctx}; check how the server was started")))
            report["cases"] += [run_case(client, c, alias, backend) for c in cases if c.alias == name]

    report["memory"] = memory_section(memory_before, read_memory())
    swapped = report["memory"]["swapouts_delta"]
    if swapped is None:
        warnings.append(warning("swap_unknown", "couldn't read vm_stat; swapping not checked"))
    elif swapped > 0:
        warnings.append(warning("swap", (
            f"macOS swapped out {swapped} pages during the run; latency and tokens/s are likely "
            "inflated, so don't promote this run to a baseline")))
    report["passed"] = (not failures and len(report["cases"]) == len(cases)
                        and all(c["status"] == "pass" for c in report["cases"]))
    report["duration_s"] = round(time.monotonic() - t0, 1)
    return report


# --- output -----------------------------------------------------------------------------

def save_report(report: dict, runs_dir: str | Path) -> None:
    runs_dir = Path(runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)
    stem = datetime.fromisoformat(report["started_at"]).strftime("%Y-%m-%dT%H-%M-%S")
    path, n = runs_dir / f"{stem}.json", 1
    while path.exists():
        path, n = runs_dir / f"{stem}-{n}.json", n + 1
    report["report_path"] = str(path)
    path.write_text(json.dumps(report, indent=1) + "\n")


def fmt(value: Any, unit: str = "", none: str = "-") -> str:
    return none if value is None else f"{value}{unit}"


def describe_alias(a: dict) -> str:
    if a["cold"] is None and a["opening_call_s"] is None:
        start = "not opened"
    elif a["cold"] is None:  # a backend that can't report what is resident, such as a frontier API
        start = f"no load to time, opening call {fmt(a['opening_call_s'], ' s')}"
    elif a["cold"]:
        before = "was loaded, unloaded first" if a["loaded_before_run"] else "wasn't loaded"
        start = f"load {fmt(a['load_s'], ' s')} ({before}), opening call {fmt(a['opening_call_s'], ' s')}"
    else:
        start = f"already resident, opening call {fmt(a['opening_call_s'], ' s')}"
    text = (f"  {a['alias']} -> {a['backend_model']}: {start}, {fmt(a['resident_gib'], ' GiB')} resident "
            f"({fmt(a['gpu_gib'], ' GiB')} on GPU), context {fmt(a['context_length'])}")
    for label in ("misroute", "error"):
        if a[label]:
            text += f"  {label.upper()} {a[label]}"
    return text


def format_table(report: dict) -> str:
    cases = report["cases"]
    passed = sum(c["status"] == "pass" for c in cases)
    verdict = "PASS" if report["passed"] else "FAIL"
    lines = [f"Local model gateway: {verdict}, {passed}/{len(cases)} cases passed in {report['duration_s']} s "
             f"(gateway {report['gateway']['url']})", "", "Backends"]
    for b in report["backends"]:
        state = {True: "up", False: "DOWN", None: "not probed"}[b["healthy"]]
        lines.append(f"  {b['kind']} {fmt(b['version'], none='')} at {b['api_base']}: {state}")
    lines += ["", "Aliases"] + [describe_alias(a) for a in report["aliases"]]
    if cases:
        rows = [("CASE", "ALIAS", "API", "RESULT", "LATENCY", "TOK/S", "ANSWER")]
        rows += [(c["id"], c["alias"], c["api"], c["failure"] or "pass", fmt(c["latency_s"], " s"),
                  fmt(c["tokens_per_s"]), c["answer_preview"] or "") for c in cases]
        widths = [max(len(r[i]) for r in rows) for i in range(6)]
        lines += ["", "Cases"]
        lines += ["  " + "  ".join(r[i].ljust(widths[i]) for i in range(6)) + "  " + r[6] for r in rows]
        lines += [f"  {c['id']} ({c['alias']}): {c['detail']}" for c in cases if c["failure"]]
    lines += ["", "Run failures: " + ("none" if not report["failures"] else "")]
    lines += [f"  {f['kind']}: {f['detail']}" for f in report["failures"]]
    lines += ["Warnings: " + ("none" if not report["warnings"] else "")]
    lines += [f"  {w['kind']}: {w['detail']}" for w in report["warnings"]]
    m = report["memory"]
    if m["swapouts_delta"] is not None:
        swap = "no swapping" if m["swapouts_delta"] == 0 else f"{m['swapouts_delta']} pages swapped out"
        lines.append(f"Memory: {swap}; readily available {m['available_gib_before']} -> {m['available_gib_after']} GiB")
    lines.append(f"Report: {report['report_path']}")
    return "\n".join(lines)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=str(GATEWAY_DIR / "litellm_config.yaml"),
                        help="gateway config (default: litellm_config.yaml in the gateway folder)")
    parser.add_argument("--cases", default=str(VALIDATOR_DIR / "cases.yaml"),
                        help="cases file (default: validator/cases.yaml)")
    parser.add_argument("--gateway", default=os.environ.get("LITELLM_GATEWAY_URL", "http://127.0.0.1:4000"))
    parser.add_argument("--api-key", default=os.environ.get("LITELLM_MASTER_KEY", "sk-local-dev"))
    parser.add_argument("--timeout", type=float, default=600, help="seconds per call (default: 600)")
    parser.add_argument("--runs-dir", default=str(GATEWAY_DIR / "runs"),
                        help="where the JSON report is written (default: runs/ in the gateway folder)")
    parser.add_argument("--unload-settle", type=float, default=UNLOAD_SETTLE_S,
                        help=f"seconds to wait after an unload before timing the load (default: {UNLOAD_SETTLE_S})")
    parser.add_argument("--keep-resident", action="store_true",
                        help="don't unload a model that is already loaded, so no load is timed for it")
    parser.add_argument("--json", action="store_true", help="print the JSON report instead of the table")
    args = parser.parse_args(argv)
    args.gateway = args.gateway.rstrip("/")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        aliases = load_alias_settings(args.cases, load_aliases(args.config))
        cases = load_cases(args.cases, aliases)
    except (ConfigError, OSError, yaml.YAMLError) as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 1
    report = run(args, aliases, cases)
    save_report(report, args.runs_dir)
    print(json.dumps(report, indent=1) if args.json else format_table(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
