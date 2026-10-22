# 2026-10-21 — other — Local model gateway baseline: deepseek-r1:14b behind LiteLLM on an M3 Pro

Project: other (the local model gateway; feeds 06-sovereign-ai-engine)

## What I did
- Built a LiteLLM gateway on `127.0.0.1:4000` in front of Ollama 0.40.6, with one alias:
  `local-reasoning` → `deepseek-r1:14b`.
  - LiteLLM is 1.103.3, with every dependency resolved as of 2026-10-06.
  - Ollama reports the model as Q4_K_M quantization, 14.8B parameters; Ollama's registry
    manifest lists its download as 8.99 GB.
  - The context window is 4096 tokens, with one model resident at a time.
- Built an end-to-end validator (`problem_first_ai/litellm/validator/`, run by the
  `local-model-e2e-validator` skill). It has 33 offline tests and four live cases:
  - arithmetic and a riddle over Chat Completions;
  - arithmetic over the Responses API;
  - a course-compatibility case: the Responses API with `reasoning_effort: low`, the course app's
    call settings.
- Settled why the load times looked unstable, with a direct experiment (below). Then made the
  runner wait 5 s after unloading before it times a load.

## What I measured (numbers + how measured)
**Baseline runs.** Measured by `validator/scripts/e2e_runner.py` through the gateway on an
Apple M3 Pro with 18 GB running macOS 15.1.1, on battery:
- **Settings:** temperature 0, output budget 2048 tokens.
- **Runs:** three consecutive runs on the final runner. Reports (local, git-ignored):
  `runs/2026-10-21T11-16-31.json`, `runs/2026-10-21T11-17-44.json`,
  `runs/2026-10-21T11-18-57.json`.
- **Latency** is end to end: thinking, answer and prompt processing.
- **Tokens per second** = output tokens ÷ end-to-end latency.

| Case | API | Latency (3 runs) | Output tokens | Tokens/s | Result |
|---|---|---|---|---|---|
| reasoning-arithmetic | chat | 17.17–17.26 s | 255 | 14.8 | pass ×3 |
| reasoning-riddle | chat | 20.78–20.79 s | 309 | 14.9 | pass ×3 |
| reasoning-responses-api | responses | 13.06–13.11 s | 193 | 14.7–14.8 | pass ×3 |
| course-compat-responses | responses | 14.63–14.68 s | 217 | 14.8 | pass ×3 |

- **Load:** 0.78–0.79 s in each run. The model was loaded before each run, so the runner unloaded
  it, waited 5 s, then timed a direct load on Ollama.
- **Opening call** (the first call through the gateway, 16-token budget): 1.16–1.19 s.
- **Resident memory:** 8.23 GiB, 100% on the GPU, context window 4096, in every run.
- **Swapping:** 0 pages swapped out in every run. Readily available memory was 2.9–3.1 GiB while
  the model was loaded (`vm_stat` free + inactive + speculative).
- **Repeatability:** identical output token counts, with each case's latency spread at 0.09 s or
  less.

**Load time vs delay after an unload** (a one-off script calling Ollama's `/api/generate`
directly, 2026-10-21 around 11:12; one sample per row):

| Delay after unload | Load | Resident |
|---|---|---|
| 0 s | 6.37 s | 8.83 GiB |
| 0 s | 5.13 s | 8.83 GiB |
| 2 s | 5.35 s | 8.23 GiB |
| 5 s | 0.80 s | 8.23 GiB |
| 10 s | 0.79 s | 8.23 GiB |
| 30 s | 0.79 s | 8.23 GiB |
| 30 s | 0.79 s | 8.23 GiB |

**Other observations:**
- **Earlier runs, same pattern:** the 9 earlier runs that reloaded straight after an unload took
  5.98–7.26 s (2026-10-21 between 01:32 and 11:10). Last night's 7 of them timed the load plus a
  16-token reply; today's 2 timed the load alone, at 6.33 s each.
- **A single slow load after hours idle:** a direct load took 5.84 s (around 10:58), after the
  model had been unloaded for hours.
- **A starved budget:** a one-off probe through the gateway around 01:20, with `max_tokens` 16.
  Chat Completions returned `finish_reason: length` with empty content and 45 characters of
  reasoning. The Responses API returned `status: incomplete` (`max_output_tokens`) with empty
  output text.
- **Memory before a restart** (around 00:44): 12 swap files totalling 12.0 GiB in
  `/System/Volumes/VM`, and 4.8 GiB "occupied by compressor" in `vm_stat`. After the restart: no
  swap files and 0.0 GiB compressed.

## What broke / what I learned
- **A load straight after an unload is slow:** within 2 s it costs about 5 s extra; 5 s or more
  later it takes about 0.8 s. Last night's "about 2 s after idling vs 6–7 s after an unload" was
  this effect.
  - *Hypothesis, untested:* Ollama waits for the GPU memory the previous load freed to be
    reported back.
  - *Hypothesis, untested:* the one 5.84 s load after hours idle came from model files that had
    dropped out of the macOS file cache. One sample only.
- **Disproved earlier:** that the runner's unload request made Ollama load the model. A direct
  test showed that an unload request for a model that isn't loaded returns in 0.02 s and loads
  nothing.
- **The gateway passes the course settings through:** the Responses API with `reasoning_effort:
  low` works for the Ollama model through LiteLLM.
- **Thinking stays out of the answer:** Chat Completions returns it as `reasoning_content`, and
  the Responses API as a separate `reasoning` output item.
- **The model ignores "reply with the number only"** and ends with `\boxed{...}`; the numeric
  check reads the final number.
- **The second brain's tooling tests had been failing on macOS** (26 errors). `Brain` didn't
  resolve its root, and macOS `/tmp` and `/var` are symlinks. Fixed, so all 34 now pass.

## Decisions (and why)
- **Wait 5 s after an unload** before timing a load, so the load figure is the model's, not the
  delay's (from the experiment above).
- **Aliases promise a role, not a model,** so baselines are recorded per backend model
  (ADR 0002).
- **The Mac is the dev loop:** capacity and utilization numbers for project 06 come from the
  cluster (ADR 0001).
- **No `drop_params` in the gateway config,** so an unsupported parameter fails loudly rather
  than being dropped silently.
- **Supply chain:** exact pins plus `exclude-newer`, after the March 2026 compromise of LiteLLM
  1.82.7 and 1.82.8.

## Links (PRs, dashboards, notebooks)
- `problem_first_ai/litellm/README.md`, `GLOSSARY.md`, `docs/adr/`, `JOURNAL.md`
- The validator: `problem_first_ai/litellm/validator/`. The skill:
  `.claude/skills/local-model-e2e-validator/` (repo root).
