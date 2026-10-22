# Local model gateway

A LiteLLM gateway on `127.0.0.1:4000` in front of open-weight models served by Ollama on this
Mac and a vendor's model reached through OpenRouter, plus a Claude skill that checks every alias
end to end after each change. To try it by hand, follow [user-guide.md](user-guide.md).

Clients call an **alias** (`local-reasoning`, `openrouter-reasoning`), never a model; the gateway
maps it to a backend model (`deepseek-r1:14b` on Ollama, `gpt-6-luna` through OpenRouter). Both
aliases answer the same cases, so each run compares them. Moving an alias to another model or to
vLLM later is a one-line change in `litellm_config.yaml`, and the validator proves nothing broke.
Terms are in [GLOSSARY.md](GLOSSARY.md); the hard-to-reverse decisions are in
[docs/adr/](docs/adr/); the rest of the design is in
[docs/2026-10-20-design-decisions.md](docs/2026-10-20-design-decisions.md). The plan for comparing
a vLLM backend on this Mac with the Ollama one (*Planned*, not built) is in
[docs/2026-10-21-vllm-metal-decisions.md](docs/2026-10-21-vllm-metal-decisions.md).

## Layout

```
problem_first_ai/litellm/
├── setup.sh                 # install Ollama, start it, pull the config's models, install Python deps
├── run_proxy.sh             # start the gateway on 127.0.0.1:4000 (logs to logs/proxy.log)
├── litellm_config.yaml      # aliases → backend models
├── pyproject.toml, uv.lock  # exact pins (LiteLLM 1.103.3), every package as of 2026-10-06
├── validator/
│   ├── cases.yaml           # prompts and checks: at least one case per alias, one check per case
│   ├── scripts/e2e_runner.py
│   └── tests/test_e2e_runner.py
├── runs/                    # one JSON report per validator run (git-ignored)
├── logs/                    # setup, proxy and Ollama logs (git-ignored)
├── .uv-cache/               # uv's package cache (git-ignored)
├── user-guide.md            # walkthrough: start everything, call each alias, run the validator
├── JOURNAL.md               # learnings, using the course journal's section names
├── GLOSSARY.md, docs/       # language and decisions
```

Two files live at the repo root, because Claude Code sessions for this work start there:

- `.claude/skills/local-model-e2e-validator/SKILL.md`: how Claude runs the validator and
  diagnoses failures.
- `.claude/settings.local.json` (git-ignored): lets Claude's sandbox use local ports and PyPI,
  sets `UV_CACHE_DIR`, and blocks writes to the course folders, `raw/` sources and `.env` files.

## Install (Apple Silicon Mac, about 18 GB of memory)

1. **Prerequisite:** [Homebrew](https://brew.sh). `setup.sh` installs Ollama and
   [uv](https://docs.astral.sh/uv/) with it if they're missing.
2. **Free memory.** `deepseek-r1:14b` was measured at 8.2–8.8 GiB resident, all on the GPU
   (`raw/story-updates/2026-10-21-local-model-gateway-baseline.md` in the second brain). If
   Activity Monitor shows heavy swap, restart the Mac first and keep other apps closed.
3. **Bootstrap:**

   ```bash
   cd problem_first_ai/litellm
   ./setup.sh
   ```

   It installs Ollama and uv if they're missing, starts Ollama with `OLLAMA_MAX_LOADED_MODELS=1
   OLLAMA_CONTEXT_LENGTH=4096` (one model loaded at a time, 4096-token context window), pulls
   only the models named in `litellm_config.yaml`, and installs the pinned Python environment.
   It's safe to re-run. If you run `ollama serve` yourself, start it with those two settings.
4. **Start the gateway** in its own terminal (Ctrl-C stops it). It always listens on
   `127.0.0.1:4000`, loopback only:

   ```bash
   ./run_proxy.sh
   ```

   It uses the master key in `LITELLM_MASTER_KEY`, or the non-secret local default
   `sk-local-dev`.

   **Keys:** the OpenRouter alias needs `OPENROUTER_API_KEY`. Unless it's already exported,
   `run_proxy.sh` takes that one variable from `problem_first_ai/.env` (`GATEWAY_ENV_FILE`
   overrides the path) and never prints it. It also sets `LITELLM_MODE=PRODUCTION`: in its
   default mode LiteLLM loads the first `.env` it finds above its install folder, which here is
   that file, with every credential in it (tested 2026-10-21; `JOURNAL.md`). Give the key a credit limit on OpenRouter, because
   anything on this Mac that knows the master key can spend through the alias.
5. **Validate:**

   ```bash
   uv run --frozen python validator/scripts/e2e_runner.py
   ```

   It loads each local alias's model (timing the load), makes an opening call to every alias, runs
   the cases, prints a table, saves a JSON report under `runs/`, and exits 0 only when every case
   passes. Each run makes a few paid calls to the OpenRouter alias. In Claude Code, ask Claude to
   validate the gateway and the skill runs this and diagnoses any failure.
6. **Call it from code:** any OpenAI client works.

   ```python
   from openai import OpenAI
   client = OpenAI(base_url="http://127.0.0.1:4000/v1", api_key="sk-local-dev")
   client.chat.completions.create(model="local-reasoning", messages=[{"role": "user", "content": "Hi"}])
   client.responses.create(model="local-reasoning", input="Hi")  # the Responses API works too
   ```

   `deepseek-r1:14b` can't call tools, so use it for questions, not tool-using agents.

## Changing things

- **Add or re-point an alias:** edit `litellm_config.yaml` (name it `<tier>-<role>`: `local`
  is this Mac, `cluster` your own NVIDIA hardware, `openrouter` a vendor's model through
  OpenRouter, `frontier` a vendor API called directly), add cases for it
  to `cases.yaml`, run `./setup.sh` to pull the model, restart the gateway, then validate.
  Re-pointing an alias starts a new baseline ([ADR 0002](docs/adr/0002-an-alias-promises-a-role.md)).
- **Add a candidate** (an alias pinned to one backend model for an experiment): name it after its
  role alias plus `-<backend>-<model>-<quantization>`, e.g. `local-reasoning-vllm-r1-14b-mlx4`,
  so it can't be re-pointed without being renamed. A candidate on a backend that is usually off
  gets its own config and cases under `experiments/`, not a place in `litellm_config.yaml`
  ([ADR 0005](docs/adr/0005-one-local-backend-at-a-time.md)).
- **Add an OpenRouter alias:** first read the model's `supported_parameters` at
  `https://openrouter.ai/api/v1/models/<model id>/endpoints`, for every upstream listed. Name the
  alias `openrouter-<role>`, like `openrouter-reasoning`, and
  reference its key as `api_key: os.environ/OPENROUTER_API_KEY`. Never write a key value into a
  file. To compare it with a local alias, list both under one case's `alias:` in `cases.yaml`.
  If `temperature` isn't in that list, give the alias `temperature: null` under `alias_settings`
  in `cases.yaml`, as `openrouter-reasoning` has; otherwise the validator sends temperature 0.
- **Record a change of plan when it's decided,** in the dated decisions doc under `docs/`.
  `/code-review` reads that doc as the spec for the change.
- **Add a frontier alias** (*Planned*): a vendor API called directly with that vendor's own key,
  for example `api_key: os.environ/OPENAI_API_KEY`, so its timings have no aggregator in them
  ([ADR 0003](docs/adr/0003-openrouter-is-its-own-tier.md)).
- **Upgrade LiteLLM:** change the pin and `exclude-newer` in `pyproject.toml` deliberately (keep
  a release at least 14 days old; releases 1.82.7 and 1.82.8 were compromised in March 2026),
  run `uv lock`, then validate.
- **Change the runner:** run its tests,
  `uv run --frozen python -m unittest discover -s validator/tests`.
