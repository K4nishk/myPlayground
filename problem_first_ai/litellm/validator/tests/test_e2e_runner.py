"""Tests for e2e_runner.py at its public seam: the command line.

Each test starts two stand-in HTTP servers, one speaking the gateway's OpenAI-compatible API
and one speaking Ollama's API, writes a config and a cases file, runs the runner as a
subprocess with --json, and asserts on the exit code and the report. Nothing inside the
runner is mocked: the network boundary is replaced, and the swap tests also replace the
vm_stat command through E2E_RUNNER_VM_STAT.

Run from problem_first_ai/litellm/:
    uv run --frozen python -m unittest discover -s validator/tests
"""

import json
import os
import time
import subprocess
import sys
import tempfile
import textwrap
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RUNNER = Path(__file__).resolve().parent.parent / "scripts" / "e2e_runner.py"
API_KEY = "sk-test"
MODEL = "deepseek-r1:14b"


class Stub:
    """A tiny HTTP server whose replies are set per test through attributes."""

    def __init__(self):
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, status, body, headers=None):
                data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for key, value in (headers or {}).items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                stub.requests.append(("GET", self.path, None, dict(self.headers), time.monotonic()))
                self._send(*stub.route("GET", self.path, None, self.headers))

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
                stub.requests.append(("POST", self.path, body, dict(self.headers), time.monotonic()))
                self._send(*stub.route("POST", self.path, body, self.headers))

        self.requests = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


class GatewayStub(Stub):
    """Speaks the slice of the LiteLLM proxy API the runner uses."""

    def __init__(self, backend):
        super().__init__()
        # Like Ollama with one model resident, a call swaps in the model the gateway routed it to.
        self.backend = backend
        self.sends_routed_header = True
        self.aliases = ["local-reasoning"]
        self.routed_model = f"ollama_chat/{MODEL}"
        self.chat = {"content": "391", "reasoning": None, "finish": "stop", "tokens": 12}
        self.responses = {"text": "42", "reasoning": "12 + 30 = 42", "status": "completed", "tokens": 9}

    def route(self, method, path, body, headers):
        if path == "/health/liveliness":
            return 200, '"I\'m alive!"'
        if headers.get("Authorization") != f"Bearer {API_KEY}":
            # What LiteLLM 1.103.3 returns for a non-master key when it has no database.
            return 400, {"error": {"message": "No connected db.", "type": "no_db_connection",
                                   "param": None, "code": "400"}}
        routed = {"x-litellm-model-name": self.routed_model} if self.sends_routed_header else {}
        if path in ("/v1/chat/completions", "/v1/responses"):
            self.backend.resident = [self.routed_model.partition("/")[2]]
        if path == "/v1/models":
            models = [{"id": a, "object": "model", "created": 0, "owned_by": "openai"} for a in self.aliases]
            return 200, {"object": "list", "data": models}
        if path == "/v1/chat/completions":
            reply = self.chat
            message = {"role": "assistant", "content": reply["content"]}
            if reply["reasoning"] is not None:
                message["reasoning_content"] = reply["reasoning"]
            return 200, {
                "id": "chatcmpl-test", "object": "chat.completion", "created": 0, "model": body["model"],
                "choices": [{"index": 0, "message": message, "finish_reason": reply["finish"]}],
                "usage": {"prompt_tokens": 19, "completion_tokens": reply["tokens"],
                          "total_tokens": 19 + reply["tokens"]},
            }, routed
        if path == "/v1/responses":
            r = self.responses
            incomplete = r["status"] == "incomplete"
            return 200, {
                "id": "resp-test", "object": "response", "created_at": 0, "model": body["model"],
                "status": r["status"],
                "incomplete_details": {"reason": "max_output_tokens"} if incomplete else None,
                "output": [
                    {"id": "rs_1", "type": "reasoning", "summary": None, "status": r["status"],
                     "content": [{"type": "output_text", "text": r["reasoning"], "annotations": []}]},
                    {"id": "msg_1", "type": "message", "role": "assistant", "status": r["status"],
                     "content": [{"type": "output_text", "text": r["text"], "annotations": []}]},
                ],
                "usage": {"input_tokens": 19, "output_tokens": r["tokens"], "total_tokens": 19 + r["tokens"]},
            }, routed
        return 404, {"error": {"message": f"no route {path}"}}


class OllamaStub(Stub):
    """Speaks the slice of Ollama's API the runner uses."""

    def __init__(self):
        super().__init__()
        self.resident = [MODEL]
        self.context_length = 4096

    def route(self, method, path, body, headers):
        if path == "/api/version":
            return 200, {"version": "0.0-test"}
        if path == "/api/ps":
            return 200, {"models": [
                {"name": m, "model": m, "size": 8 * 2**30, "size_vram": 8 * 2**30,
                 "context_length": self.context_length}
                for m in self.resident
            ]}
        if path == "/api/generate":
            if body.get("keep_alive") == 0:  # Ollama's way to unload a model
                self.resident = [m for m in self.resident if m != body.get("model")]
                return 200, {"model": body.get("model"), "done": True, "done_reason": "unload"}
            # No prompt: Ollama only loads the model (one resident at a time).
            self.resident = [body.get("model")]
            return 200, {"model": body.get("model"), "done": True, "done_reason": "load"}
        return 404, {"error": f"no route {path}"}


class RunnerTestCase(unittest.TestCase):
    def setUp(self):
        self.ollama = OllamaStub()
        self.gateway = GatewayStub(self.ollama)
        self.addCleanup(self.gateway.stop)
        self.addCleanup(self.ollama.stop)
        self.dir = Path(tempfile.mkdtemp())
        self.config = self.dir / "litellm_config.yaml"
        self.config.write_text(textwrap.dedent(f"""\
            model_list:
              - model_name: local-reasoning
                litellm_params:
                  model: ollama_chat/{MODEL}
                  api_base: {self.ollama.url}
                  num_ctx: 4096
            """))
        self.cases = self.dir / "cases.yaml"
        self.write_cases("""\
            cases:
              - id: arithmetic
                alias: local-reasoning
                api: chat
                prompt: What is 17 × 23? Reply with the number only.
                output_budget: 2048
                checks:
                  - {type: exact_numeric, expected: 391}
            """)

    def write_cases(self, text):
        self.cases.write_text(textwrap.dedent(text))

    def run_runner(self, *extra, env=None, json_output=True):
        args = [sys.executable, str(RUNNER), "--config", str(self.config), "--cases", str(self.cases),
                "--gateway", self.gateway.url, "--api-key", API_KEY, "--runs-dir", str(self.dir / "runs"),
                "--unload-settle", "0", *extra]
        if json_output:
            args.append("--json")
        proc = subprocess.run(args, capture_output=True, text=True, timeout=60, env={**os.environ, **(env or {})})
        report = json.loads(proc.stdout) if json_output and proc.stdout.strip().startswith("{") else None
        return proc, report

    def case(self, report, case_id):
        return next(c for c in report["cases"] if c["id"] == case_id)


class PassingRun(RunnerTestCase):
    def test_a_correct_answer_passes_and_exits_zero(self):
        proc, report = self.run_runner()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(report["passed"])
        self.assertEqual(self.case(report, "arithmetic")["status"], "pass")


class ExactNumeric(RunnerTestCase):
    def test_the_boxed_value_is_the_answer_even_when_numbers_follow_it(self):
        self.gateway.chat["content"] = "17 × 23 = 17 × 20 + 17 × 3 = 340 + 51.\n\\boxed{391} (that is 17 × 23)"
        proc, report = self.run_runner()
        self.assertEqual(self.case(report, "arithmetic")["status"], "pass", report)

    def test_without_a_box_the_last_number_is_the_answer(self):
        self.gateway.chat["content"] = "It might be 391, but on reflection it is 392."
        proc, report = self.run_runner()
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.case(report, "arithmetic")["failure"], "check_failed")


class AnswerFailures(RunnerTestCase):
    def test_hitting_the_output_budget_is_budget_exhausted(self):
        self.gateway.chat.update(content="", reasoning="Let me think about 17 times", finish="length")
        proc, report = self.run_runner()
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.case(report, "arithmetic")["failure"], "budget_exhausted")

    def test_a_blank_answer_is_empty_answer(self):
        self.gateway.chat.update(content="  \n", finish="stop")
        proc, report = self.run_runner()
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.case(report, "arithmetic")["failure"], "empty_answer")


class Reasoning(RunnerTestCase):
    def test_thinking_inside_think_tags_is_not_the_answer(self):
        # A backend without a reasoning parser puts the thinking inline in the answer text.
        self.gateway.chat["content"] = "<think>\nIs 17 × 23 = 391? Yes.\n</think>\n"
        proc, report = self.run_runner()
        self.assertEqual(self.case(report, "arithmetic")["failure"], "empty_answer")

    def test_reasoning_length_is_reported_from_either_source(self):
        self.gateway.chat.update(content="<think>abc</think>391", reasoning="12345")
        proc, report = self.run_runner()
        result = self.case(report, "arithmetic")
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["reasoning_chars"], 8)  # "12345" from the field + "abc" from the tags


class Contains(RunnerTestCase):
    def setUp(self):
        super().setUp()
        self.write_cases("""\
            cases:
              - id: riddle
                alias: local-reasoning
                api: chat
                prompt: Which is heavier, a kilogram of feathers or a kilogram of steel?
                output_budget: 2048
                checks:
                  - {type: contains, expected: [same, equal]}
            """)

    def test_any_expected_phrase_passes_regardless_of_case(self):
        self.gateway.chat["content"] = "They weigh the SAME: one kilogram each."
        proc, report = self.run_runner()
        self.assertEqual(self.case(report, "riddle")["status"], "pass", report)

    def test_no_expected_phrase_fails(self):
        self.gateway.chat["content"] = "Steel is heavier."
        proc, report = self.run_runner()
        self.assertEqual(self.case(report, "riddle")["failure"], "check_failed")


class ResponsesApi(RunnerTestCase):
    def setUp(self):
        super().setUp()
        self.write_cases("""\
            cases:
              - id: responses-sum
                alias: local-reasoning
                api: responses
                prompt: What is 12 + 30? Reply with the number only.
                output_budget: 2048
                checks:
                  - {type: exact_numeric, expected: 42}
            """)

    def test_the_message_text_is_the_answer_and_reasoning_is_counted(self):
        proc, report = self.run_runner()
        result = self.case(report, "responses-sum")
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["reasoning_chars"], len("12 + 30 = 42"))
        self.assertTrue(any(r[1] == "/v1/responses" for r in self.gateway.requests))

    def test_a_cases_reasoning_effort_is_sent_the_way_the_course_sends_it(self):
        # The course calls ChatOpenAI(use_responses_api=True, reasoning_effort="low").
        self.write_cases("""\
            cases:
              - id: course-compat
                alias: local-reasoning
                api: responses
                reasoning_effort: low
                prompt: What is 12 + 30? Reply with the number only.
                output_budget: 2048
                checks:
                  - {type: exact_numeric, expected: 42}
            """)
        proc, report = self.run_runner()
        self.assertEqual(self.case(report, "course-compat")["status"], "pass", report)
        sent = [r[2] for r in self.gateway.requests if r[1] == "/v1/responses"]
        self.assertEqual(sent[-1].get("reasoning"), {"effort": "low"})

    def test_an_incomplete_response_is_budget_exhausted(self):
        self.gateway.responses.update(status="incomplete", text="")
        proc, report = self.run_runner()
        self.assertEqual(self.case(report, "responses-sum")["failure"], "budget_exhausted")


class Misroute(RunnerTestCase):
    def test_the_gateway_sending_the_alias_to_another_model_is_a_misroute(self):
        self.gateway.routed_model = "ollama_chat/llama3.1:8b"
        proc, report = self.run_runner()
        self.assertEqual(proc.returncode, 1)
        result = self.case(report, "arithmetic")
        self.assertEqual(result["failure"], "misroute")
        self.assertEqual(result["routed_model"], "ollama_chat/llama3.1:8b")

    def test_without_the_routing_header_the_resident_model_still_reveals_a_misroute(self):
        self.gateway.sends_routed_header = False
        self.gateway.routed_model = "ollama_chat/llama3.1:8b"
        proc, report = self.run_runner()
        self.assertEqual(self.case(report, "arithmetic")["failure"], "misroute")


class OpeningCall(RunnerTestCase):
    """Before its cases, each alias's model is loaded straight on the backend (timed as the load),
    then one opening call goes through the gateway."""

    def alias_row(self, report):
        return next(a for a in report["aliases"] if a["alias"] == "local-reasoning")

    def backend_posts(self, keep_alive_zero):
        return [r for r in self.ollama.requests
                if r[1] == "/api/generate" and (r[2].get("keep_alive") == 0) == keep_alive_zero]

    def test_a_loaded_model_is_unloaded_then_loaded_and_the_load_is_timed(self):
        proc, report = self.run_runner()
        self.assertEqual((len(self.backend_posts(True)), len(self.backend_posts(False))), (1, 1))
        row = self.alias_row(report)
        self.assertEqual((row["loaded_before_run"], row["cold"]), (True, True))
        self.assertIsNotNone(row["load_s"])
        self.assertIsNotNone(row["opening_call_s"])

    def test_after_an_unload_the_runner_waits_before_timing_the_load(self):
        # Measured: a load within 2 s of an unload takes about 5 s longer than one 5 s later.
        proc, report = self.run_runner("--unload-settle", "1")
        unload, load = self.backend_posts(True)[0], self.backend_posts(False)[0]
        self.assertGreaterEqual(load[4] - unload[4], 1.0)
        self.assertEqual(self.alias_row(report)["unload_settle_s"], 1.0)

    def test_a_model_that_isnt_resident_is_loaded_without_an_unload(self):
        self.ollama.resident = []
        proc, report = self.run_runner()
        self.assertEqual((len(self.backend_posts(True)), len(self.backend_posts(False))), (0, 1))
        row = self.alias_row(report)
        self.assertEqual((row["loaded_before_run"], row["cold"]), (False, True))

    def test_keep_resident_neither_unloads_nor_loads_a_resident_model(self):
        proc, report = self.run_runner("--keep-resident")
        self.assertFalse(any(r[1] == "/api/generate" for r in self.ollama.requests))
        row = self.alias_row(report)
        self.assertEqual((row["cold"], row["load_s"]), (False, None))
        self.assertIsNotNone(row["opening_call_s"])

    def test_the_resident_models_memory_and_context_window_are_recorded(self):
        proc, report = self.run_runner()
        row = self.alias_row(report)
        self.assertEqual((row["resident_gib"], row["gpu_gib"], row["context_length"]), (8.0, 8.0, 4096))

    def test_a_misrouted_opening_call_fails_the_run(self):
        self.gateway.routed_model = "ollama_chat/llama3.1:8b"
        proc, report = self.run_runner()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("misroute", [f["kind"] for f in report["failures"]])

    def test_a_context_window_other_than_the_configs_warns(self):
        self.ollama.context_length = 2048
        proc, report = self.run_runner()
        self.assertEqual(proc.returncode, 0, report)
        self.assertIn("context_mismatch", [w["kind"] for w in report["warnings"]])


FAKE_VM_STAT = """\
import pathlib, sys
counter = pathlib.Path(sys.argv[1])
calls = int(counter.read_text()) if counter.exists() else 0
counter.write_text(str(calls + 1))
print("Mach Virtual Memory Statistics: (page size of 16384 bytes)")
print("Pages free:                               65536.")
print("Pages inactive:                          131072.")
print("Pages speculative:                            0.")
print(f"Swapouts:                                {calls * int(sys.argv[2])}.")
"""


class SwapWarning(RunnerTestCase):
    def fake_vm_stat(self, pages_per_call):
        script = self.dir / "fake_vm_stat.py"
        script.write_text(FAKE_VM_STAT)
        return {"E2E_RUNNER_VM_STAT": f"{sys.executable} {script} {self.dir / 'calls'} {pages_per_call}"}

    def test_swapping_during_the_run_warns_but_does_not_fail(self):
        proc, report = self.run_runner(env=self.fake_vm_stat(pages_per_call=500))
        self.assertEqual(proc.returncode, 0, report)
        self.assertIn("swap", [w["kind"] for w in report["warnings"]])
        self.assertGreater(report["memory"]["swapouts_delta"], 0)

    def test_no_swapping_means_no_warning(self):
        proc, report = self.run_runner(env=self.fake_vm_stat(pages_per_call=0))
        self.assertEqual(report["warnings"], [])
        self.assertEqual(report["memory"]["swapouts_delta"], 0)
        self.assertEqual(report["memory"]["available_gib_before"], 3.0)  # (65536 + 131072) pages × 16 KiB


class Output(RunnerTestCase):
    def test_by_default_a_table_is_printed_and_the_report_is_saved(self):
        proc, _ = self.run_runner(json_output=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("1/1 cases passed", proc.stdout)
        self.assertIn("arithmetic", proc.stdout)
        saved = list((self.dir / "runs").glob("*.json"))
        self.assertEqual(len(saved), 1)
        self.assertIn(str(saved[0]), proc.stdout)
        self.assertTrue(json.loads(saved[0].read_text())["passed"])

    def test_the_json_report_names_the_saved_file(self):
        proc, report = self.run_runner()
        self.assertTrue(Path(report["report_path"]).is_file())

    def test_a_case_for_an_alias_the_config_lacks_is_a_config_error(self):
        self.write_cases("""\
            cases:
              - {id: orphan, alias: local-text, api: chat, prompt: hi, output_budget: 16}
            """)
        proc, report = self.run_runner()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("config error", proc.stderr)
        self.assertIn("local-text", proc.stderr)


class CaseCoverage(RunnerTestCase):
    def test_an_alias_without_cases_is_a_config_error(self):
        self.config.write_text(textwrap.dedent(f"""\
            model_list:
              - model_name: local-reasoning
                litellm_params: {{model: ollama_chat/{MODEL}, api_base: "{self.ollama.url}"}}
              - model_name: local-text
                litellm_params: {{model: ollama_chat/llama3.1:8b, api_base: "{self.ollama.url}"}}
            """))
        proc, report = self.run_runner()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("config error", proc.stderr)
        self.assertIn("local-text", proc.stderr)

    def test_a_case_without_checks_is_a_config_error(self):
        self.write_cases("""\
            cases:
              - {id: unchecked, alias: local-reasoning, api: chat, prompt: hi, output_budget: 16}
            """)
        proc, report = self.run_runner()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("unchecked", proc.stderr)


def closed_port_url():
    """A loopback URL that refuses connections."""
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    return f"http://127.0.0.1:{port}"


class RunLevelFailures(RunnerTestCase):
    def failures(self, report):
        return [f["kind"] for f in report["failures"]]

    def test_an_unreachable_gateway_fails_the_run_without_sending_cases(self):
        self.gateway.url = closed_port_url()
        proc, report = self.run_runner()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("gateway_unreachable", self.failures(report))
        self.assertEqual(report["cases"], [])

    def test_each_aliass_backend_model_is_recorded_even_when_the_run_stops_early(self):
        self.gateway.url = closed_port_url()
        proc, report = self.run_runner()
        row = next(a for a in report["aliases"] if a["alias"] == "local-reasoning")
        self.assertEqual(row["backend_model"], MODEL)
        self.assertIsNone(row["opening_call_s"])

    def test_an_unhealthy_backend_fails_the_run_without_sending_cases(self):
        self.ollama.stop()
        proc, report = self.run_runner()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("backend_unhealthy", self.failures(report))
        self.assertEqual(report["cases"], [])

    def test_the_gateway_serving_other_aliases_than_the_config_fails_the_run(self):
        self.gateway.aliases = ["local-reasoning", "local-text"]
        proc, report = self.run_runner()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("alias_mismatch", self.failures(report))

    def test_a_rejected_api_key_fails_the_run(self):
        proc, report = self.run_runner("--api-key", "sk-wrong")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("gateway_rejected_key", self.failures(report))


if __name__ == "__main__":
    unittest.main()
