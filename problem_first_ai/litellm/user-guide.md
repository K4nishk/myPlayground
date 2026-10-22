# User guide: try the local and OpenRouter models through the gateway

A walkthrough at the terminal: start everything, call each alias by hand, compare them, then run
the validator. Terms (alias, backend model, load, opening call, case) are in
[GLOSSARY.md](GLOSSARY.md).

| Alias | Backend model | Tier |
|---|---|---|
| `local-reasoning` | `deepseek-r1:14b` on Ollama, on this Mac | `local` |
| `openrouter-reasoning` | `gpt-6-luna` through OpenRouter | `openrouter` |

`openrouter-reasoning` timings include OpenRouter's hop and its choice of upstream, so they aren't
frontier timings ([ADR 0003](docs/adr/0003-openrouter-is-its-own-tier.md)).

## Before you start

- **Done once:** `./setup.sh` in this folder (installs Ollama and the pinned Python environment,
  pulls the model). See the [README](README.md).
- **The OpenRouter key** is `OPENROUTER_API_KEY` in `problem_first_ai/.env`. The gateway reads
  that one variable and nothing else from the file. Give the key a credit limit on OpenRouter:
  every call to `openrouter-reasoning` costs credits.
- **Free memory:** the local model takes about 8.2–8.8 GiB, all on the GPU (baseline note,
  `raw/story-updates/2026-10-21-local-model-gateway-baseline.md`). Quit memory-heavy apps.
- **Three terminal windows:** A for Ollama, B for the gateway, C for everything else.

You only ever type the gateway's master key, `sk-local-dev`: a non-secret local default for a
gateway that listens on `127.0.0.1` only. Never paste the OpenRouter key into a command.

## 1. Start Ollama (window A)

Skip this if `curl -s localhost:11434/api/version` already answers.

```bash
OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_CONTEXT_LENGTH=4096 ollama serve
```

Check from window C: `curl -s localhost:11434/api/version` prints `{"version":"0.40.6"}`.

## 2. Start the gateway (window B)

```bash
~/Documents/Github/myPlayground/problem_first_ai/litellm/run_proxy.sh
```

- **Good:** `Starting LiteLLM gateway on http://127.0.0.1:4000`, then LiteLLM's startup lines.
- **Bad:** a line starting `WARNING: OPENROUTER_API_KEY is neither exported nor readable`. The
  local alias still works, but `openrouter-reasoning` will fail until you add the key and restart.
- Restart the gateway (Ctrl-C, then the same command) after any change to `litellm_config.yaml`
  or to the key.

## 3. Check the gateway is up (window C)

```bash
curl -s http://127.0.0.1:4000/health/liveliness; echo
curl -s -H "Authorization: Bearer sk-local-dev" http://127.0.0.1:4000/v1/models | python3 -m json.tool
```

Expect `"I'm alive!"`, then a list whose `id`s are `local-reasoning` and `openrouter-reasoning`.

## 4. Ask the local model

```bash
curl -s http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-local-dev" -H "Content-Type: application/json" \
  -d '{"model": "local-reasoning", "temperature": 0, "max_tokens": 2048,
       "messages": [{"role": "user", "content": "What is 17 x 23? Reply with the number only."}]}' \
  | python3 -m json.tool
```

- **The answer** is in `choices[0].message.content`. This model writes a worked solution ending
  in `\boxed{391}`, even when asked for the number only.
- **The thinking** is in `reasoning_content`, kept out of the answer by the gateway.
- **Timing:** each baseline case took 13–21 s end to end (baseline note). If the model wasn't
  loaded, this is a cold call: it also waits for the load.

## 5. Ask the OpenRouter model

The same call to the other alias, without `temperature`: none of the upstreams OpenRouter lists
for `gpt-6-luna` takes one, and the gateway refuses `temperature: 0` for it on the Responses API
(the comment above `alias_settings` in `validator/cases.yaml` cites both).

```bash
curl -s http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-local-dev" -H "Content-Type: application/json" \
  -d '{"model": "openrouter-reasoning", "max_tokens": 2048,
       "messages": [{"role": "user", "content": "What is 17 x 23? Reply with the number only."}]}' \
  | python3 -m json.tool
```

Expect `"content": "391"`. Without a temperature, its answers can vary from run to run.

## 6. Compare both aliases on both APIs

This calls each alias through Chat Completions and through the Responses API with the course
app's setting (`reasoning_effort` low). For each call it prints the time, the backend model the
gateway says it used (the `x-litellm-model-name` header) and the end of the answer.

```bash
cd ~/Documents/Github/myPlayground/problem_first_ai/litellm
uv run --frozen python - <<'EOF'
import time
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:4000/v1", api_key="sk-local-dev")
prompt = "What is 17 x 23? Reply with the number only."
for alias in ("local-reasoning", "openrouter-reasoning"):
    extra = {"temperature": 0} if alias == "local-reasoning" else {}  # see step 5
    for api in ("chat", "responses"):
        started = time.monotonic()
        if api == "chat":
            raw = client.chat.completions.with_raw_response.create(
                model=alias, messages=[{"role": "user", "content": prompt}], max_tokens=2048, **extra)
            answer = raw.parse().choices[0].message.content
        else:
            raw = client.responses.with_raw_response.create(
                model=alias, input=prompt, max_output_tokens=2048, reasoning={"effort": "low"}, **extra)
            answer = raw.parse().output_text
        seconds = time.monotonic() - started
        routed = raw.headers.get("x-litellm-model-name") or "(no routing header)"
        tail = " ".join(answer.split())[-25:]  # the answer's end, on one line
        print(f"{alias:21} {api:9} {seconds:5.1f} s  {routed:30} ...{tail}")
EOF
```

Expect four lines. The local ones show `ollama_chat/deepseek-r1:14b`, the OpenRouter ones
`openrouter/openai/gpt-6-luna`. A different backend model there is a misroute.

## 7. Run the validator

The validator does all of this properly: it times the local model's load, makes an opening call
to each alias, runs every case in `validator/cases.yaml` on both aliases, checks each answer, and
watches for misroutes and swapping.

```bash
cd ~/Documents/Github/myPlayground/problem_first_ai/litellm
uv run --frozen python validator/scripts/e2e_runner.py
```

Or, in a Claude session started at the repo root, say "validate the gateway". Claude runs the
same command and diagnoses any failure.

A good run prints `Local model gateway: PASS, 8/8 cases passed`, `Warnings: none` and
`Memory: no swapping`, and exits with code 0. The JSON report is saved under `runs/`. Only a run
with no warnings can become a baseline; ask Claude to record it as a story update.

## 8. When something goes wrong

| You see | It means | Do this |
|---|---|---|
| `curl: (7) Failed to connect` to port 4000 | The gateway isn't running | Step 2 |
| `alias_mismatch` in the validator | The gateway started with an older config | Restart the gateway |
| The `WARNING` line from step 2 | No `OPENROUTER_API_KEY` in `problem_first_ai/.env` | Add it, restart the gateway |
| 401 on `openrouter-reasoning` | OpenRouter refused the key: revoked, expired, or with an expiry longer than your account allows (seen 2026-10-21; `JOURNAL.md`) | Make a new key, put it in `.env`, restart the gateway |
| 402 on `openrouter-reasoning` | The key's credit limit or your balance ran out | Check it on openrouter.ai |
| 400 `UnsupportedParamsError` | A parameter the model doesn't take, such as `temperature` on `openrouter-reasoning` | Leave that parameter out |
| A `swap` warning | macOS swapped during the run, so the timings are inflated | Quit apps and run again; don't use it as a baseline |
| A local call after a break is slow | It's a cold call: the model is loading | Normal. Ollama unloads an idle model after its `keep_alive`, 5 minutes by default ([Ollama API docs](https://github.com/ollama/ollama/blob/main/docs/api.md)) |

The gateway's log is `logs/proxy.log` in this folder. The validator skill's diagnosis table
(`.claude/skills/local-model-e2e-validator/SKILL.md` at the repo root) covers every failure kind.

## 9. Stop

Press Ctrl-C in window B (the gateway), then in window A (Ollama), if you started it there.
