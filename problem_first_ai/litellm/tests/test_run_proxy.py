"""Tests for run_proxy.sh's key handling, at its command line.

run_proxy.sh is run against a stand-in `uv` that replaces the OS command: the key read still runs
the real interpreter in the gateway's environment, but "starting the gateway" only reports what
the gateway would be given (whether each variable is set, never its value). The script is copied
with its port check pointed at a free port, because the real gateway may be running on 4000.

The last tests import the pinned LiteLLM itself, to show why run_proxy.sh sets LITELLM_MODE.

Run from problem_first_ai/litellm/:
    uv run --frozen python -m unittest discover -s tests
"""

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GATEWAY = Path(__file__).resolve().parent.parent
RUN_PROXY = GATEWAY / "run_proxy.sh"
STAND_IN_UV = """\
#!/bin/sh
case "$*" in
  *" litellm "*)
    echo "LITELLM_MODE=${LITELLM_MODE:-unset}"
    echo "OPENROUTER_API_KEY ${OPENROUTER_API_KEY:+set}"
    echo "OTHER_SECRET ${OTHER_SECRET:+set}" ;;
  *)
    [ -n "$STAND_IN_PYTHON_FAILS" ] && exit 1
    shift 2  # "run --frozen"
    exec "$REAL_UV" run --frozen --project "$GATEWAY_DIR" "$@" ;;
esac
"""


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def clean_environment() -> dict:
    """The test's environment without anything run_proxy.sh reads or sets."""
    return {k: v for k, v in os.environ.items()
            if k not in ("OPENROUTER_API_KEY", "OTHER_SECRET", "LITELLM_MODE", "GATEWAY_ENV_FILE")}


class KeyHandling(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        script = self.dir / "run_proxy.sh"
        script.write_text(RUN_PROXY.read_text().replace("127.0.0.1/4000", f"127.0.0.1/{free_port()}"))
        self.bin = self.dir / "bin"
        self.bin.mkdir()
        (self.bin / "uv").write_text(STAND_IN_UV)
        (self.bin / "uv").chmod(0o755)
        self.env_file = self.dir / "course.env"

    def start(self, env_file_text=None, **env):
        if env_file_text is not None:
            self.env_file.write_text(env_file_text)
        environment = {**clean_environment(), "PATH": f"{self.bin}:{os.environ['PATH']}",
                       "REAL_UV": shutil.which("uv"), "GATEWAY_DIR": str(GATEWAY),
                       "GATEWAY_ENV_FILE": str(self.env_file), **env}
        proc = subprocess.run(["bash", str(self.dir / "run_proxy.sh")], env=environment,
                              capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return (self.dir / "logs" / "proxy.log").read_text().splitlines()

    def test_without_a_key_the_warning_is_the_first_line_of_the_log(self):
        log = self.start()
        self.assertTrue(log[0].startswith("WARNING: OPENROUTER_API_KEY"), log)

    def test_a_failed_key_read_still_puts_the_warning_in_the_log(self):
        log = self.start("OPENROUTER_API_KEY=sk-or-test\n", STAND_IN_PYTHON_FAILS="1")
        self.assertTrue(log[0].startswith("WARNING: OPENROUTER_API_KEY"), log)

    def test_an_exported_key_reaches_the_gateway_without_a_warning(self):
        log = self.start(OPENROUTER_API_KEY="sk-or-test")
        self.assertIn("OPENROUTER_API_KEY set", log)
        self.assertFalse(any(line.startswith("WARNING") for line in log), log)

    def test_only_the_openrouter_key_is_taken_from_the_env_file(self):
        log = self.start("OPENROUTER_API_KEY=sk-or-test\nOTHER_SECRET=not-for-the-gateway\n")
        self.assertIn("OPENROUTER_API_KEY set", log)
        self.assertIn("OTHER_SECRET ", log)  # reported as not set
        self.assertFalse(any(line.startswith("WARNING") for line in log), log)

    def test_the_gateway_runs_in_litellm_production_mode(self):
        log = self.start(OPENROUTER_API_KEY="sk-or-test")
        self.assertIn("LITELLM_MODE=PRODUCTION", log)


class PinnedLiteLLM(unittest.TestCase):
    """Why run_proxy.sh sets LITELLM_MODE: by default, importing LiteLLM's proxy loads a .env file."""

    def dotenv_loads(self, mode):
        code = ("import dotenv; calls = []\n"
                "dotenv.load_dotenv = lambda *a, **k: calls.append(1) or False\n"
                "import litellm.proxy.proxy_cli\n"
                "print(len(calls))")
        environment = {**clean_environment(), "LITELLM_LOCAL_MODEL_COST_MAP": "True"}
        if mode:
            environment["LITELLM_MODE"] = mode
        proc = subprocess.run([sys.executable, "-c", code], env=environment,
                              capture_output=True, text=True, timeout=180)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return int(proc.stdout.split()[-1])

    def test_by_default_importing_the_proxy_loads_a_dotenv_file(self):
        self.assertGreater(self.dotenv_loads(None), 0)

    def test_in_production_mode_importing_the_proxy_loads_no_dotenv_file(self):
        self.assertEqual(self.dotenv_loads("PRODUCTION"), 0)


if __name__ == "__main__":
    unittest.main()
