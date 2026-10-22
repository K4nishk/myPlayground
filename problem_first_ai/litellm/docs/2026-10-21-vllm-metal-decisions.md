# 2026-10-21 — Local model gateway — vLLM on Metal (N7) — design decisions

Decided by Kanishk in a `/grill-with-docs` session in the repo root; written up by Claude. This
is a plan: **nothing was installed, pulled or started**. Terms are in [`GLOSSARY.md`](../GLOSSARY.md)
(new this session: *Experiment*, *Footprint*). The two hard-to-reverse decisions are
[ADR 0004](adr/0004-vllm-metal-from-pinned-wheels.md) and
[ADR 0005](adr/0005-one-local-backend-at-a-time.md).

**Goal:** serve the `local` tier on vLLM through vllm-metal and compare it with the Ollama baseline
([`raw/story-updates/2026-10-21-local-model-gateway-baseline.md`](../../../raw/story-updates/2026-10-21-local-model-gateway-baseline.md)).
Per [ADR 0001](adr/0001-mac-is-the-dev-loop.md), the point is that the Mac runs the same server the
cluster will. The point is not capacity.

## Starting point

- **Hardware and backend:** M3 Pro, 18 GB, macOS 15.1.1. `local-reasoning` → `deepseek-r1:14b`
  (Q4_K_M) on Ollama 0.40.6, with a 4096-token context window and one model resident at a time.
- **Baseline (in the note above):** 14.7–14.9 tokens/s on all four cases, 8.23 GiB resident and
  100% on the GPU, no swapping.
- **Gateway:** LiteLLM 1.103.3. `openrouter-reasoning` goes to `gpt-6-luna` through OpenRouter.

## Decided

### The experiment's shape
- **A Candidate, not a re-point.** The vLLM side is the Candidate `local-reasoning-vllm-r1-14b-mlx4`.
  `local-reasoning` stays on Ollama and isn't touched until the experiment closes. Its baseline,
  keyed by alias plus backend model, is the Ollama side
  ([ADR 0002](adr/0002-an-alias-promises-a-role.md)).
- **Candidate names** are the role alias plus `-<backend>-<model>-<quantization>`, so a candidate
  can't be re-pointed without being renamed.
- **Re-pointing is never automatic.** If the Candidate meets the bar below, the experiment's
  story update *proposes* re-pointing `local-reasoning`, and Kanishk decides it separately. That
  re-point starts a new baseline. vllm-metal is Alpha, so it backs a Candidate, not yet a role
  alias.
- **One local backend at a time** ([ADR 0005](adr/0005-one-local-backend-at-a-time.md)). Ollama is
  stopped, not just unloaded, while vLLM runs.
- **Where the Candidate is configured:** its own config and cases in
  `experiments/2026-10-vllm-metal/`. That `cases.yaml` is a frozen copy of the four cases in
  `validator/cases.yaml`, with only the alias changed. The Ollama runs use the normal config and
  cases, which is the baseline's procedure plus `openrouter-reasoning`: about 15 paid calls over
  three runs. `run_proxy.sh` gains an optional config path; the default is unchanged.
- **Single stream only.** Requests go one at a time, as the validator sends them, and the vLLM
  server is limited to one sequence. No throughput or concurrency claim comes from the Mac.

### vllm-metal: version, install, model
- **vllm-metal v0.30.0 with vLLM 0.30.0**, frozen there. v0.31.0 becomes eligible under the
  14-day rule on 2026-10-27; moving to it is a deliberate re-pin, like a LiteLLM upgrade.
- **Installed from pinned wheels in its own uv project**, `backends/vllm-metal/`
  ([ADR 0004](adr/0004-vllm-metal-from-pinned-wheels.md)). The pins:
  - **Python 3.12,** managed by uv. No `brew install` is needed anywhere in this plan.
  - **vLLM:** `vllm-0.30.0+cpu-cp312-cp312-macosx_11_0_arm64.whl`, sha256
    `fd9adfd566a8afa4ecbdf36b04bab10ebf43cd9ca18eca4b0a0bf2013b8de135`, published 2026-09-22.
  - **vllm-metal:** `vllm_metal-0.30.0-cp312-cp312-macosx_15_0_arm64.whl`, sha256
    `3955de8b2c75b633ef889b70fa469a4db661a0c5bb2f78e36272d68b16da9353`, published 2026-09-23.
  - **`mlx-lm`:** at git commit `9e6acca691e64d6d8bb808c328fcdea459099cca` (2026-08-25), the commit
    v0.30.0 names.
  - **`transformers==5.17.0`:** pinned explicitly. v0.30.0 sets no upper bound, 5.18.0 broke vLLM
    startup for at least one model, and vLLM 0.31 then capped it below 5.18.
  - **Everything else from PyPI:** under `exclude-newer` set to the build date minus 14 days.
- **Model:** `mlx-community/DeepSeek-R1-Distill-Qwen-14B-4bit` at revision
  `b39611728ed604538a2a18212ce33b02f99d8de2`. It's 4-bit with group size 64, 8.32 GB, and the
  same distill as Ollama's `deepseek-r1:14b`.
  - **Fairness caveat:** that works out to about 4.5 bits per weight, against roughly 4.9 for
    Ollama's 9.0 GB Q4_K_M (*illustrative*: file size ÷ 14.8B parameters). It's the closest
    available match, not the same file.
  - **What follows:** temperature-0 answers can differ between the two, so the comparison is
    about pass rate and tokens/s, not identical token counts.
  - **Rejected:** the same GGUF on both backends (vllm-metal rejects K-quants); Q8_0 (about 16 GB,
    too big); the 14B AWQ build (9.99 GB, and vllm-metal hasn't verified AWQ for this
    architecture).
- **8B fallback:** `mlx-community/DeepSeek-R1-0528-Qwen3-8B-4bit` (4.62 GB, revision
  `b9b5af4fa18feb8cdbccdadf3aad2c83d0abbe51`) against Ollama's `deepseek-r1:8b`.
  - **That Ollama model** is the 0528 Qwen3-8B distill, not Llama-8B: `ollama show` reports qwen3,
    8.2B, Q4_K_M, and Ollama's tag page agrees.
  - **When it applies:** at a 4096-token context window, vLLM won't start, gives the KV cache no
    blocks, or swaps during a run.
  - **Two new candidates:** there's no 8B baseline, so falling back makes both sides candidates,
    `local-reasoning-vllm-r1-8b-mlx4` and `local-reasoning-ollama-r1-8b-q4km`.
  - `deepseek-r1:8b` stays on disk until the experiment closes. It's deleted only if the fallback
    wasn't needed.
- **macOS stays at 15.1.1.** vllm-metal needs macOS 15+, and no one has reported running it
  on 15.1. If it won't run there, that's the experiment's result. macOS isn't updated mid-experiment.

### The vLLM server
- **`backends/vllm-metal/run_vllm.sh`** runs in the foreground like `run_proxy.sh`, with the same
  port-in-use guard, and logs to `logs/vllm.log`. Its flags:
  - `--host 127.0.0.1 --port 8000`, fixed;
  - the model with `--revision`;
  - `--max-model-len 4096 --max-num-seqs 1 --max-num-batched-tokens 4096`;
  - `--reasoning-parser deepseek_r1`.

  `--gpu-memory-utilization` stays at its default for the first start. It's lowered only if that
  start swaps or fails, and every flag is recorded in the story update.
- **What it times:** a vLLM load is the server start, until `/health` answers and `/v1/models`
  lists the model. The script times it, and reads `vm_stat` wired memory before launch and once
  ready. This figure is a different quantity from Ollama's on-request load (0.78–0.79 s in the
  baseline), so the two are never shown side by side.
- **Weights:** `HF_HOME` is a git-ignored `backends/vllm-metal/.hf-cache/`, a folder Claude's
  sandbox can write to. The 8.32 GB download is pinned by revision and needs Kanishk's approval.
  While serving, `HF_HUB_OFFLINE=1`.
- **Telemetry stays on.**
  - **vLLM's usage reports to its maintainers** are left at vLLM's default, which is on.
  - **Local telemetry:** after each vLLM alias's cases, the runner saves the `vllm:` lines from
    `/metrics` into the run report. That's the same path Prometheus will scrape on the cluster.
  - LiteLLM's `telemetry: false` is unchanged.

### Through the gateway
- **The route:** `hosted_vllm/mlx-community/DeepSeek-R1-Distill-Qwen-14B-4bit` with `api_base:
  http://127.0.0.1:8000/v1`. The expected context window goes in
  `model_info: {context_window: 4096}`, not `num_ctx`. The pinned LiteLLM accepts extra
  `model_info` fields (`extra="allow"` in `types/router.py`). *Hypothesis:* `num_ctx` would be
  forwarded to vLLM as an unknown request field.
- **The Responses API goes to vLLM natively.** Verified in the pinned LiteLLM source:
  `hosted_vllm` sends Responses API calls to vLLM's own `/v1/responses`, whereas `ollama_chat`
  calls go through LiteLLM's conversion to Chat Completions. `use_chat_completions_api: true` would
  force the conversion, but it stays off. If a Responses API case fails natively, that's a
  recorded result. One earlier report had reasoning missing from vLLM's `/v1/responses`
  (vllm-metal issue #301).
- **Thinking stays out of the answer, in two layers:**
  - **The server-side parser.** The R1 distill's chat template always opens the reply with
    `<think>\n`, so the model's output carries only a closing `</think>`. LiteLLM's fallback
    split (`_parse_content_for_reasoning`) and the runner's `split_thinking` both need both tags.
    `--reasoning-parser deepseek_r1` does the separation on the server. It exists upstream, but no
    test of it on Metal has been reported.
  - **The runner's safety net.** The runner treats text before an unmatched `</think>` as
    thinking.
- **`reasoning_effort` is accepted, not obeyed.** For `ollama_chat`, LiteLLM turns
  `low`/`medium`/`high` into `think: true`. For `hosted_vllm`, it passes the value through. The
  R1 distill's template has no switch to turn thinking off. So `course-compat-responses` proves
  the parameter travels end to end, not that it changes anything.

### The runner (`validator/scripts/e2e_runner.py`)
- **A `VLLMBackend`** beside `OllamaBackend`, registered for `hosted_vllm`. It:
  - probes the server root, since `api_base` ends in `/v1`;
  - checks health on `/health` and reads the version from `/version`;
  - probes the served models on `/v1/models`. If the alias's backend model isn't listed, that's a
    misroute, through the existing check, and `max_model_len` is the context window;
  - never loads or unloads anything. A vLLM alias is always reported as already resident.
- **Reasoning** is read from either `reasoning_content` or `reasoning`. vLLM 0.30.0 renamed the
  field; LiteLLM 1.103.3 reads both, but the runner shouldn't depend on which name the gateway
  passes on.
- **Footprint:**
  - The report gets `footprint_gib` and `footprint_method`. On the Mac, the method is the change
    in wired memory from `vm_stat`, read before and after each Ollama load and after each alias's
    last case. That last reading catches vLLM's KV cache, which is committed only once requests
    write to it.
  - Each backend's own figure (`resident_gib` from Ollama's `/api/ps`) stays a separate field.
  - `footprint` is blocked in Claude's sandbox, so per-process tools are out.
  - On the cluster, the method is *Planned* as GPU memory from `nvidia-smi`.
- **Tests** go at the existing seams: the command line, stand-in HTTP servers and
  `E2E_RUNNER_VM_STAT`, so there's no new seam. A `VLLMStub` sits beside `OllamaStub`, and each
  test is written red first:
  1. a served Candidate passes, and the table shows vLLM up and already resident;
  2. vLLM down gives `backend_unhealthy`, and no case is sent;
  3. `/v1/models` serving another model is a misroute;
  4. the runner never asks vLLM to load or unload;
  5. `max_model_len` differing from `model_info.context_window` warns `context_mismatch`;
  6. text before an unmatched `</think>` is thinking, not the answer;
  7. reasoning is read from either field;
  8. the footprint is recorded, using the fake `vm_stat`;
  9. the `/metrics` snapshot lands in the report.

### What's measured, and the bar (*Proposed*)
- **The conditions:** three consecutive runs on each side, in the same sitting, on the same
  power source. Each run uses temperature 0, an output budget of 2048 tokens, and the four cases.
  The 2026-10-21 baseline stays the reference; the head-to-head uses the fresh runs.
- **Per case:** pass or fail, latency, output tokens, tokens/s (output tokens ÷ end-to-end
  latency, as in the baseline), `reasoning_chars`, and whether any `</think>` reached the answer.
- **Per alias:**
  - the load: Ollama's timed by the runner, vLLM's by `run_vllm.sh`;
  - the opening call;
  - the footprint, plus each backend's own figure;
  - swap-outs and readily available memory;
  - the vLLM `/metrics` snapshot.
- **Versions and flags recorded:** vllm-metal, vLLM, mlx, the `mlx-lm` commit, the model revision,
  every `run_vllm.sh` flag, Ollama, LiteLLM, macOS and the power source.
- **The experiment is complete** when each side has three passing runs with no swap and no
  misroute. If v0.30.0 can't install or start on macOS 15.1.1, that's a recorded result instead.
- **The footprint method is trusted** only if the Ollama runs' footprint is within 10% of
  `/api/ps`'s figure. Otherwise memory is reported in each backend's own accounting and not
  compared.
- **The Candidate meets the bar** if all of these hold:
  - 4/4 cases pass in all three runs;
  - every case keeps thinking out of the answer (`reasoning_chars` > 0, and no `</think>` in the
    answer);
  - tokens/s is no more than 10% below the fresh Ollama runs on any case;
  - its footprint is no more than 1 GiB above Ollama's.

  The bar is "not slower" rather than "faster" because, under ADR 0001, the gain is running the
  same server the cluster will run.

### Runbook and sequence
- **A general runbook,** `docs/runbooks/measure-a-backend.md`, covers:
  - the preconditions: nothing else resident, the power source, swap at 0;
  - stopping the other backends, then starting and checking this one;
  - recording versions and flags;
  - three runs, and reading memory;
  - which reports and logs to keep, and how they become a story update.

  Each step gives its exact command, what success looks like, and what to save if it fails. A
  failed attempt is a result too. The Mac section is written first; a cluster section comes later.
- **The experiment's README** in `experiments/2026-10-vllm-metal/` fills in its exact values and
  points to the runbook.
- **A `/wizard` script,** `experiments/2026-10-vllm-metal/measure.sh`, walks Kanishk through the
  steps only he can do, runs the validator three times on each side, and lists the saved reports.
- **Who does what.** Claude's sandbox can't list or signal processes (`pgrep` is blocked), so:
  - **Kanishk** stops the gateway and Ollama before anything is installed or loaded.
  - **The build session** installs and smoke-starts vLLM.
  - **The measurement session** runs Ollama three times first, which also checks the machine
    still matches the baseline, then vLLM three times, then restores Ollama with `setup.sh`'s
    settings.
  - The experiment's story update is drafted in `runs/` and goes to `raw/story-updates/` with
    Kanishk's approval.

## Planned work (dependency order)

1. **The runner:** `VLLMBackend`, the unmatched-`</think>` fix, both reasoning fields, the
   footprint, `model_info.context_window` and the `/metrics` snapshot, test-first. It needs no
   install. Not blocked.
2. **The backend project:** `backends/vllm-metal/` (`pyproject.toml`, `uv.lock`,
   `.python-version`, `run_vllm.sh`, `.gitignore`), `bash -n` added to `tools/check.sh`, then the
   install, the model download and a smoke start, after Kanishk has stopped the gateway and Ollama.
   Not blocked.
3. **The experiment folder:** the config, the cases, the README, and `run_proxy.sh`'s config path.
   Blocked by 1 and 2.
4. **The runbook and the wizard.** Blocked by 1–3.
5. **The measurement session:** the runs, the story update and an ingest into the second brain.
   Blocked by 1–4.

## Risks (open)

- No one has reported vllm-metal on macOS 15.1.1. The pull requests that report a macOS version
  ran 15.6 and 15.7.8.
- No test of the `deepseek_r1` reasoning parser on Metal has been reported; only `qwen3`'s has.
- Reasoning may be missing from `/v1/responses` (vllm-metal issue #301).
- **Memory fit is tight** (*illustrative*, from the research's arithmetic): about 2.8 GB of budget
  after the 14B's 8.32 GB of weights. Fixes after v0.30.0 that would help (the KV commit probe,
  sleep mode, the memory guides) are too new to use.

## Conflicts

> **Conflict (2026-10-21):** `ollama show deepseek-r1:14b` now lists the capabilities `tools,
> thinking, completion`, and its template renders `tool_calls`. The
> [2026-10-20 decisions](2026-10-20-design-decisions.md) (and the README, journal and wiki) say
> it "cannot call tools (its Ollama prompt template has no tools section)". Whether it actually
> calls tools reliably is untested. Settling it is outside N7; it needs its own session.

## Sources

- **The vllm-metal facts** (versions, hashes, dates, formats, flags, issues) are from a read-only
  web research pass on 2026-10-21:
  - the releases API, <https://api.github.com/repos/vllm-project/vllm-metal/releases>
  - the v0.30.0 `pyproject.toml`, `install.sh`, `docs/` and `vllm_metal/` source, under
    <https://raw.githubusercontent.com/vllm-project/vllm-metal/v0.30.0/>
  - vLLM's v0.30.0 release, <https://api.github.com/repos/vllm-project/vllm/releases/tags/v0.30.0>
  - its reasoning-outputs docs, <https://raw.githubusercontent.com/vllm-project/vllm/v0.30.0/docs/features/reasoning_outputs.md>
  - the Hugging Face model APIs, <https://huggingface.co/api/models/mlx-community/DeepSeek-R1-Distill-Qwen-14B-4bit?blobs=true>
  - Ollama's tags, <https://ollama.com/library/deepseek-r1/tags>
  - the transformers issue, <https://github.com/vllm-project/vllm/issues/59562>
- **LiteLLM behaviour** comes from reading the pinned 1.103.3 source in `.venv`:
  - `llms/hosted_vllm/chat/transformation.py` and `llms/hosted_vllm/responses/transformation.py`
  - `utils.py` (LiteLLM's Responses API settings for each kind of backend)
  - `responses/main.py` (`use_chat_completions_api`)
  - `llms/ollama/chat/transformation.py` (how `reasoning_effort` maps to `think`)
  - `litellm_core_utils/prompt_templates/common_utils.py` (`_extract_reasoning_content`, `_parse_content_for_reasoning`)
  - `types/router.py` (`model_info` accepts extra fields)
- **Local, read-only checks this session:** `ollama show` for both models, `ollama list`, and
  `uv python list`; `footprint` and `pgrep` blocked in the sandbox; `vm_stat` readable.
- **Measured figures** are from `raw/story-updates/2026-10-21-local-model-gateway-baseline.md`.
