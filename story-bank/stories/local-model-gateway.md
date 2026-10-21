---
id: local-model-gateway
title: One front door to local and frontier models, with a test that proves every route
status: in-progress
projects: [wiki/synthesis/2026-10-20-local-model-gateway-plan.md]
last_synced: 2026-10-21
evidence: [raw/story-updates/2026-10-21-local-model-gateway-baseline.md, raw/story-updates/2026-10-21-openrouter-alias-first-runs.md]
---

# One front door to local and frontier models, with a test that proves every route

> **One-liner:** I put a LiteLLM gateway in front of an open-weight reasoning model on an 18 GB
> Mac, plus an end-to-end validator. Every case passes over both OpenAI APIs at about 14.8
> tokens/s, with the model fully on the GPU and no swapping.

## Situation
Comparing a frontier API with self-hosted models (project 06) needs one interface that every
client calls, whatever serves the model behind it. On an 18 GB Mac, a 14B model also leaves little
memory headroom.

## Task
Stand up one alias, `local-reasoning`, behind a gateway that speaks both Chat Completions and the
Responses API. Build a validator that proves after every change that each alias answers correctly
from the right model, without swapping.

## Action
- **Aliases name a role, not a model** (ADR 0002), so moving to vllm-metal or a smaller model is a
  config change, and every baseline is recorded per backend model.
- **The supply chain is pinned** to an exact LiteLLM release and to every dependency as of 14 days
  before the build, after the March 2026 compromise of two LiteLLM releases.
- **The validator was built test-first** at the command-line boundary, against stand-in HTTP
  servers. Answers are judged on their final number, a starved budget is reported as its own
  failure, and misroutes are caught from two independent sources.
- **A puzzling cold-start figure was settled by experiment** rather than a guess. Loads within 2 s
  of an unload were about 5 s slower, so the validator now waits 5 s before timing a load.
- **A second backend shares every case.** `openrouter-reasoning` → `gpt-6-luna` through OpenRouter
  answers the same prompts under the same checks as the local model. OpenRouter got its own tier,
  because its hop and its choice of upstream mean its timings aren't frontier timings (ADR 0003).
- **Three hidden defaults, found from symptoms and fixed:**
  - LiteLLM was loading the course's whole `.env`. Now the gateway reads only the one key it needs.
  - A cooldown turned one 401 into four 429s. Cooldowns are now off.
  - The gateway refused `temperature: 0` for `gpt-6-luna`. That alias is now sent no temperature,
    and the report records what each alias was sent.

## Result
From the [baseline note](../../raw/story-updates/2026-10-21-local-model-gateway-baseline.md):
- Four cases passed in each of three runs, including the course app's call settings (Responses
  API, `reasoning_effort: low`).
- 13.06–20.79 s per case, end to end, at 14.7–14.9 tokens/s.
- The model loads in 0.78–0.79 s and takes 8.23 GiB, all on the GPU. No pages were swapped out.
- A load within 2 s of an unload took 5.13–6.37 s, against 0.79–0.80 s from 5 s on.

From the [OpenRouter first-runs note](../../raw/story-updates/2026-10-21-openrouter-alias-first-runs.md).
This isn't a baseline: macOS swapped during three of the four runs.
- `openrouter-reasoning` passed all four cases in two runs, at 1.10–2.36 s per case. Those
  latencies include OpenRouter's hop.
- `local-reasoning` passed 4/4 in all four runs, with identical output token counts each time.

## Talking points
- Why an alias should promise a role rather than a model, and what that does to baselines.
- Measuring one thing per number: load, opening call and steady-state calls kept apart.
- Supply-chain hygiene for AI tooling after a real PyPI compromise.
- Turning an unexplained timing into a measured effect, and keeping its cause labelled a
  hypothesis.
- A dependency's defaults are part of your system: an implicit `.env` load, and a retry policy
  that hid the real error.
- Why "frontier" should mean the vendor's own API, not an aggregator in front of it.

## Angles
- **Status update (3 lines):** A LiteLLM gateway fronts `deepseek-r1:14b` on the Mac and
  `gpt-6-luna` through OpenRouter, over both OpenAI APIs. Both aliases pass the same four cases.
  Next: a run with no swapping for the first local-vs-OpenRouter baseline, then vllm-metal.
- **Interview (2-minute STAR):** TBD. Refine with the story skill once the frontier comparison
  exists.
- **Résumé bullet:** Built a pinned LiteLLM gateway and a test-first end-to-end validator for local
  open-weight models; measured 14.8 tokens/s and a 0.8 s load, fully on the GPU, on an 18 GB Mac.

## Open threads
- A local-vs-OpenRouter baseline: needs a run with no warnings.
- A `frontier-*` alias for a vendor API called directly, once a direct key with credits exists.
- `seed` for the OpenRouter alias, which is best effort and untried.
- vllm-metal on the Mac: *Planned* as an experiment, with a Candidate alias run against the
  Ollama baseline (decided 2026-10-21). `local-reasoning` is re-pointed only if the Candidate
  meets the bar and you decide to.
- Why loads straight after an unload, or after Ollama's own idle unload, are slow: untested
  hypotheses only.

## Changelog
- 2026-10-21 — First draft, from the baseline note and the project journal.
- 2026-10-21 — Synced with the OpenRouter first-runs note and the journal's afternoon entry: the
  second backend, the three hidden defaults, and results labelled as not a baseline.
- 2026-10-21 — Synced with the vLLM-on-Metal decisions: the vllm-metal thread is now a
  *Planned* experiment with a Candidate, not a re-point. No new results.
