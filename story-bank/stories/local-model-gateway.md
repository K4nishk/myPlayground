---
id: local-model-gateway
title: One front door to local and frontier models, with a test that proves every route
status: in-progress
projects: [wiki/synthesis/2026-10-20-local-model-gateway-plan.md]
last_synced: 2026-10-21
evidence: [raw/story-updates/2026-10-21-local-model-gateway-baseline.md]
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

## Result
From the [baseline note](../../raw/story-updates/2026-10-21-local-model-gateway-baseline.md):
- Four cases passed in each of three runs, including the course app's call settings (Responses
  API, `reasoning_effort: low`).
- 13.06–20.79 s per case, end to end, at 14.7–14.9 tokens/s.
- The model loads in 0.78–0.79 s and takes 8.23 GiB, all on the GPU. No pages were swapped out.
- A load within 2 s of an unload took 5.13–6.37 s, against 0.79–0.80 s from 5 s on.

## Talking points
- Why an alias should promise a role rather than a model, and what that does to baselines.
- Measuring one thing per number: load, opening call and steady-state calls kept apart.
- Supply-chain hygiene for AI tooling after a real PyPI compromise.
- Turning an unexplained timing into a measured effect, and keeping its cause labelled a
  hypothesis.

## Angles
- **Status update (3 lines):** A LiteLLM gateway now fronts `deepseek-r1:14b` on the Mac over both
  OpenAI APIs. An end-to-end validator passes 4/4 cases at about 14.8 tokens/s with no swapping.
  Next: the frontier alias, then vllm-metal.
- **Interview (2-minute STAR):** TBD. Refine with the story skill once the frontier comparison
  exists.
- **Résumé bullet:** Built a pinned LiteLLM gateway and a test-first end-to-end validator for local
  open-weight models; measured 14.8 tokens/s and a 0.8 s load, fully on the GPU, on an 18 GB Mac.

## Open threads
- The frontier alias (`gpt-6-luna`) and a same-cases comparison with the local model.
- vllm-metal as the Mac's backend: a re-pointed alias and a new baseline.
- Why a load straight after an unload is slow: untested hypotheses only.

## Changelog
- 2026-10-21 — First draft, from the baseline note and the project journal.
