# Journal — local model gateway

Learnings from building a LiteLLM gateway in front of local models, filed under the four section
names of the Assignment 1 journal so they sit next to the course notes. Each entry records what
actually happened. Measured figures come from the baseline note
`raw/story-updates/2026-10-21-local-model-gateway-baseline.md` in the second brain.

## 2026-10-20/21 — first slice: `local-reasoning` on `deepseek-r1:14b`

### Part 2 · Tool Integration

- **Adding a backend is like adding a tool.** One entry in `litellm_config.yaml` plus at least one
  case in `cases.yaml`. The runner reads both, so a new alias gets health, routing and memory
  verification with no code change.
- **The model decides what it can be used for.** `deepseek-r1:14b`'s Ollama template has no tools
  section, so it can serve question answering but not tool calls or a ReAct loop. Tool use needs
  a tools-capable alias first.

### Part 4 · Evaluation Metrics

- **Which check for which answer.** The cases reuse the course dataset's check names:
  `exact_numeric` for arithmetic, `contains` for a fact. A non-empty, finished answer is required
  before any check runs. Routing and memory are verified on every call, separately from answer
  quality.
- **Where matching the raw text breaks.** Asked for "the number only", the model still wrote a
  worked solution ending in `\boxed{391}`. Matching the whole text fails a correct answer, and
  "any number in the text" passes on an intermediate step. The check reads the final number
  instead (the last `\boxed{}`, else the last number), and a unit test pins both cases.
- **The budget is part of the measurement.** Through the gateway with a 16-token output budget,
  both a Chat Completions and a Responses API call came back empty, because the model was still
  thinking. A starved budget looks exactly like a broken model unless it's reported as its own
  failure (`budget_exhausted`).
- **What's not here yet:** an LLM-as-a-judge. The riddle case accepts several phrasings with
  `contains`; a judge comes in once there's a calibrated rubric.

### Mega Bonus

The validator is a small version of a prompt-and-model testing system: a dataset (`cases.yaml`),
named checks, one JSON report per run under `runs/`, and a rule that only a run with no warnings
becomes a baseline. What a real platform adds: history across runs, two models compared on the
same cases, and judge-based scoring.

### Overall Reflection

- **Choices that mattered.**
  - Clients call aliases that name a role, not a model (ADR 0002), so moving to vLLM or a smaller
    model is a config change, and baselines are recorded per backend model.
  - The runner is driven by the config, so it tests whatever the gateway is meant to serve.
  - The supply chain is pinned twice over: an exact LiteLLM version, and `exclude-newer` so every
    transitive package resolves as of 14 days before the build.
- **Surprises.**
  - LiteLLM keeps thinking out of the answer: Chat Completions puts it in `reasoning_content`, and
    the Responses API returns a separate `reasoning` item. Calling Ollama directly with
    `think: false`, the model still wrote `<think>` into its reply.
  - With no database, LiteLLM rejects a wrong key with 400 "No connected db.", not 401.
  - I wrote down a timing quirk as a runner bug before testing it; a two-line test disproved it.
    Test a hypothesis before recording it as a finding.
- **What slowed me down.**
  - Before a restart the Mac had 12 GiB in swap and 4.8 GiB compressed, and quitting apps didn't
    release it. A restart did.
  - A Claude session resumed from the parent folder silently lost its sandbox settings, which are
    only read from the folder a session starts in.
- **What I'll carry forward.** Put a stable interface in front of anything you plan to swap, and
  keep a regression test that exercises the interface, not the thing behind it.

## 2026-10-21 (morning) — review follow-ups

### Part 4 · Evaluation Metrics

- **Separate what you're timing.** The old "cold call" mixed the model load with a 16-token
  reply. The runner now times a direct load on Ollama, then the opening call through the gateway.
- **An experiment beats a guess.** I varied the delay between unloading and loading the model and
  timed each load directly. Within 2 s of an unload, loads took 5.1–6.4 s; from 5 s on, about
  0.8 s every time. The earlier "about 2 s vs 6–7 s" puzzle was this effect. The runner now waits
  5 s after an unload, and the baseline load is a steady 0.78–0.79 s. Why the wait matters is
  still a hypothesis: Ollama waiting for freed GPU memory to be reported back.
- **Course compatibility is now a case.** The Responses API with `reasoning_effort: low`, the
  course app's call settings, passes through the gateway to the local model.

### Overall Reflection

- **A guardrail earns its keep on day one.** The repo had no pre-commit hook and no CI. The first
  run of the new checks (`tools/check.sh`) turned up 26 failing tests in the second brain's own
  tooling. The cause was a path bug on macOS, where `/tmp` and `/var` are symlinks, and it was
  fixed in one line.
- **Least privilege takes a deny list.** With sessions starting at the repo root, Claude's sandbox
  can write the whole repo by default. It has no "only these folders" switch inside the working
  directory, but an `Edit(...)` deny rule blocks both the file tools and shell writes. So the
  course folders, curated `raw/` sources and `.env` files are now denied.
- **Course material is easy to leak by accident.** A course dataset prompt almost went into the
  public cases file and was caught on review. It's now a written review rule
  (`CODING_STANDARDS.md`).
