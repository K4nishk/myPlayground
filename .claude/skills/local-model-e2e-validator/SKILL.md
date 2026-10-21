---
name: local-model-e2e-validator
description: End-to-end check of the local model gateway (LiteLLM on 127.0.0.1:4000 in front of Ollama, plus an OpenRouter alias). Use after any change to litellm_config.yaml, an alias, a backend or the pinned versions; when asked to verify, smoke-test or regression-test the local models, the OpenRouter alias or the gateway; or when an alias fails, is slow or is misrouted.
---

# Local model e2e validator

Proves that every alias in `problem_first_ai/litellm/litellm_config.yaml` still answers
correctly through the gateway. Terms (alias, backend model, load, opening call, case, check,
run, misroute, budget exhausted, baseline) are defined in `problem_first_ai/litellm/GLOSSARY.md`.
The code lives in `problem_first_ai/litellm/validator/`.

## Steps

1. **Run the validator** from the repo root:

   ```bash
   uv run --frozen --project problem_first_ai/litellm python problem_first_ai/litellm/validator/scripts/e2e_runner.py --json
   ```

   Give the command a 10-minute timeout: each local alias's model is loaded fresh and every case
   waits for a full answer, thinking included. Each run also makes paid calls to the OpenRouter
   alias, so run it when asked or after a change, never in a loop. Done when the command exits:
   code 0 with a JSON report means every case passed, code 1 with a JSON report means something
   failed. A `config error:`
   line on stderr and no JSON means `litellm_config.yaml` or `validator/cases.yaml` is broken;
   report that line and stop.

2. **Read the report.** Look at:
   - `passed` and `failures` (problems at run level)
   - `cases[].failure` and `cases[].detail`
   - `warnings`
   - `aliases`: backend model, `loaded_before_run`, `load_s`, `opening_call_s`, `misroute`,
     memory, GPU share and context window. An alias on a vendor API (the `openrouter` or
     `frontier` tier) has only the opening call and `misroute`: its backend can't report what is
     loaded.
   - `memory`

   Done when you can name every run-level failure, every failed case and every warning.

3. **Diagnose each failure without changing anything**, using the table below. Take addresses
   from the report (`gateway.url`, `backends[].api_base`), not from memory. Done when each
   failure has a cause backed by a command's output, or "unknown" plus what you checked.

4. **Report to the developer**: the status tables (format below), then one line per failure with
   its cause and the fix you propose. Ask before restarting Ollama or the gateway, pulling a
   model (a multi-gigabyte download), or editing `litellm_config.yaml` or `validator/cases.yaml`.
   Done when the developer has the tables and every proposed fix is waiting on their answer.

## Diagnosis

Process and port listings (`lsof`, `ps`) may be blocked inside Claude's sandbox. If one is, say
so and ask the developer to run it.

| Failure | Meaning | Read-only commands |
|---|---|---|
| any, with `Operation not permitted` on 127.0.0.1 | This Claude session's sandbox can't use local ports: it started somewhere other than the repo root, where `.claude/settings.local.json` allows them | Tell the developer to restart Claude Code from the repo root |
| `gateway_unreachable` | Nothing answers at the gateway URL | `curl -s <gateway.url>/health/liveliness`; `lsof -nP -iTCP:<port> -sTCP:LISTEN`; the end of `problem_first_ai/litellm/logs/proxy.log` |
| `gateway_rejected_key` | The key isn't the master key. With no database, LiteLLM answers 400 "No connected db." | Compare `LITELLM_MASTER_KEY` with the key `run_proxy.sh` started with (default `sk-local-dev`) |
| `gateway_error` | `/v1/models` failed for another reason | The end of `logs/proxy.log` |
| `backend_unhealthy` | A backend isn't answering | `curl -s <api_base>/api/version`; `ollama ps` |
| `alias_mismatch` | The gateway serves other aliases than the config lists | `curl -s -H "Authorization: Bearer $LITELLM_MASTER_KEY" <gateway.url>/v1/models` against the config; an older config needs a gateway restart (ask first) |
| `misroute` (run level or case) | A call was served by another model | The detail says whether the gateway header or the backend's resident list disagreed; `ollama ps`; the alias's `model:` line in the config |
| `budget_exhausted` | The model hit `output_budget` before finishing | A large `reasoning_chars` means it spent the budget thinking; propose a larger budget for that case |
| `empty_answer` | The model finished with no answer, often all thinking | `ollama show <model>` for its template and capabilities |
| `check_failed` | The answer is wrong | Quote `answer_preview`. At temperature 0 (the default) a re-run repeats it; an alias with `temperature: null` in `alias_settings` (the OpenRouter one) may answer differently, so re-run once before calling it wrong |
| `error` | The call raised an exception | The detail, then the end of `logs/proxy.log` |
| `error` on the OpenRouter alias | The detail carries the HTTP status. 400 `UnsupportedParamsError`: the gateway refused a parameter the model doesn't accept (the config has no `drop_params`, on purpose). 401: OpenRouter refused the key: missing, revoked, or with an expiry longer than the account allows (seen 2026-10-21; `problem_first_ai/litellm/JOURNAL.md`). 402: the key's credit limit or the account balance ran out. 429 from OpenRouter: rate limited. A 429 saying "No deployments available… cooldown" is LiteLLM pausing the alias after an earlier failure, which `disable_cooldowns` in the config should prevent: find that first failure | Quote the detail's message. For 401, the first line of `logs/proxy.log`: `run_proxy.sh` writes a warning there when it found no `OPENROUTER_API_KEY`. Never read, print or copy any `.env` file; checking the key and its credits on openrouter.ai is the developer's job |

Warnings never fail a run:

- `swap`: macOS swapped during the run, so latency and tokens/s are inflated. Don't promote the
  run to a baseline. Suggest quitting memory-heavy apps.
- `swap_unknown`: `vm_stat` was unavailable (not macOS), so swapping wasn't checked.
- `context_mismatch`: the backend's context window differs from the config's `num_ctx`; the
  server was probably started without `OLLAMA_CONTEXT_LENGTH`.

## Status tables

The values below are illustrative; fill them in from the report.

```
| Alias                | Backend model     | Temperature | Load  | Opening call | Resident (GPU) | Context | Cases | Result |
|----------------------|-------------------|-------------|-------|--------------|----------------|---------|-------|--------|
| local-reasoning      | deepseek-r1:14b   | 0           | 6.0 s | 1.1 s        | 8.2 GiB (8.2)  | 4096    | 4/4   | PASS   |
| openrouter-reasoning | openai/gpt-6-luna | not sent    | n/a   | 0.9 s        | n/a            | n/a     | 4/4   | PASS   |

| Case                 | API  | local-reasoning      | openrouter-reasoning |
|----------------------|------|----------------------|----------------------|
| reasoning-arithmetic | chat | pass, 17.2 s, 14.8/s | pass, 2.1 s          |
```

List failed cases first, each with its alias and `detail`. End with the swap result and
`report_path`. An OpenRouter latency includes OpenRouter's hop, its choice of upstream and the
network, so say so when you compare it with a local one; it is not a frontier timing (ADR 0003).

## Rules

- Never loosen a check in `cases.yaml`, or raise a budget, to make a run pass without the
  developer agreeing.
- Only a run with no warnings may become a baseline. Baselines are dated notes under
  `raw/story-updates/` in the second brain; their numbers are cited from there.
- After changing the runner, run its tests from the repo root:
  `uv run --frozen --project problem_first_ai/litellm python -m unittest discover -s problem_first_ai/litellm/validator/tests`
