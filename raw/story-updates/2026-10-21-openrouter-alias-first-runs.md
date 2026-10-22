# 2026-10-21 — other — OpenRouter alias: first runs beside the local model (not a baseline)

Project: other (the local model gateway; feeds 06-sovereign-ai-engine)

## What I did
- Added a second alias to the LiteLLM gateway: `openrouter-reasoning` → `gpt-6-luna` through
  OpenRouter. It was created as `frontier-reasoning` and renamed the same day, because OpenRouter
  adds a hop and picks the upstream (`problem_first_ai/litellm/docs/adr/0003-openrouter-is-its-own-tier.md`).
- The four validator cases now name both aliases, so every run answers the same prompts under the
  same checks on both.
- `run_proxy.sh` sets `LITELLM_MODE=PRODUCTION` and reads only `OPENROUTER_API_KEY` from
  `problem_first_ai/.env`.
- The gateway config sets `disable_cooldowns`.
- The validator sends `openrouter-reasoning` no temperature; every other alias gets 0.

## What I measured (numbers + how measured)
Measured by `validator/scripts/e2e_runner.py` through the gateway on an Apple M3 Pro with 18 GB
running macOS 15.1.1, on 2026-10-21. Four runs, with local, git-ignored reports:
`runs/2026-10-21T17-29-18.json`, `runs/2026-10-21T17-50-15.json`,
`runs/2026-10-21T18-03-59.json` and `runs/2026-10-21T19-07-46.json`.

**Not a baseline.** macOS swapped during three of the four runs: 436, 73,464 and 10,692 pages
swapped out, in run order from 17:50. During the last run, another Claude session on this Mac was
working on vllm-metal.

**`openrouter-reasoning`**, in the two runs where every case passed (18:03 and 19:07):

| Case | API | Latency (18:03, 19:07) | Output tokens | Answer |
|---|---|---|---|---|
| reasoning-arithmetic | chat | 1.70 s, 1.99 s | 21, 21 | `391` |
| reasoning-riddle | chat | 2.36 s, 2.28 s | 41, 43 | "They weigh the same: one kilogram each." |
| reasoning-responses-api | responses | 1.10 s, 1.24 s | 20, 20 | `42` |
| course-compat-responses | responses | 1.23 s, 1.41 s | 20, 17 | `80` |

- **Latency** is end to end through the gateway and OpenRouter, so it includes OpenRouter's hop and
  its choice of upstream. It isn't a frontier timing (ADR 0003).
- **Output tokens** are as the gateway reports them. Tokens per second isn't meaningful for answers
  this short.
- **Opening call** (16-token budget): 1.22 s, 1.69 s and 1.66 s, in the runs from 17:50.
- **Reasoning text returned:**
  - The riddle returned 397 characters (17:50), 440 (18:03) and 0 (19:07).
  - The other cases returned none in any run.
- **The two chat cases also passed at 17:50:** 2.39 s with 21 tokens, and 2.40 s with 52 tokens.

**`local-reasoning`** (deepseek-r1:14b on Ollama 0.40.6, temperature 0) passed 4/4 in all four
runs:

| Case | API | Latency (4 runs) | Output tokens |
|---|---|---|---|
| reasoning-arithmetic | chat | 17.28–18.23 s | 255 |
| reasoning-riddle | chat | 20.91–21.70 s | 309 |
| reasoning-responses-api | responses | 13.14–13.78 s | 193 |
| course-compat-responses | responses | 14.71–15.26 s | 217 |

- Output token counts were identical in every run, and match the 2026-10-21 baseline note.
- **Loads:** in all four runs the model wasn't loaded beforehand, because Ollama had unloaded it
  after idling. The load took 7.08 s, 6.83 s, 8.15 s and 7.09 s, at 8.83 GiB, all on the GPU. For
  comparison, the baseline note has 0.78–0.79 s at 8.23 GiB, timed 5 s after the runner's own
  unload.
- **Readily available memory** before → after each run: 7.4 → 1.5, 8.9 → 1.7, 7.3 → 1.5 and
  8.8 → 1.5 GiB.

## What broke / what I learned
- **17:29, the first key:** the opening call got OpenRouter's 401, "This API key expires later than
  this account allows. Create a key that expires within the account's maximum key lifetime."
  - The four cases after it got LiteLLM's own 429, "No deployments available … All deployments for
    selected model are in cooldown", not the 401.
  - Fixed with a new key and `disable_cooldowns`.
- **17:50, temperature:** LiteLLM refused both Responses API cases with 400 `UnsupportedParamsError`:
  "openai/gpt-6-luna doesn't support temperature=0 while reasoning is active".
  - The two chat cases passed with temperature 0 sent. Whether OpenRouter applied it is unknown.
  - Fixed by sending this alias no temperature.
- **LiteLLM's `.env` loading:** importing the proxy's command line with the key unset put every
  variable from `problem_first_ai/.env` into the environment. I counted them; no value was printed.
  With `LITELLM_MODE=PRODUCTION`, none appeared.
- **Varying answers:** with no temperature, the riddle's answer and its token count varied between
  runs.
- *Hypothesis, untested:* why a load after Ollama's own idle unload (6.83–8.15 s, 8.83 GiB) is slower
  than one 5 s after the runner's unload (0.78–0.79 s, 8.23 GiB). Three of the four runs here also
  swapped, so memory pressure may add to it.

## Decisions (and why)
- **OpenRouter's key, not OpenAI's,** because the OpenRouter account holds the budget for these
  calls.
- **OpenRouter is its own tier.** `frontier-*` waits for a vendor API called directly (ADR 0003).
- **The gateway reads only the one key** from the course's `.env`, rather than LiteLLM loading the
  whole file.
- **No cooldowns:** one backend per alias and no fallback, so a pause only hides the real error.
- **No temperature for the OpenRouter alias:** OpenRouter lists none for `gpt-6-luna`, and the
  pinned LiteLLM refuses 0 for it on the Responses API.

## Next
- A run with no warnings, for the first local-vs-OpenRouter baseline: quit memory-heavy apps, with
  no other session loading models.

## Links (PRs, dashboards, notebooks)
- `problem_first_ai/litellm/JOURNAL.md` (2026-10-21, afternoon), `docs/adr/0003-openrouter-is-its-own-tier.md`,
  `user-guide.md`, `validator/cases.yaml`
