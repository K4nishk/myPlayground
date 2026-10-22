---
title: LLM Evaluation (Quality, Latency, Throughput, Cost)
type: concept
status: draft
tags: [evaluation, llm-as-judge, latency, throughput, benchmarking]
sources: [raw/roadmaps/2026-10-18-sovereign-ai-engine-blueprint.md, raw/story-updates/2026-10-21-local-model-gateway-baseline.md, problem_first_ai/litellm/JOURNAL.md]
related: [concepts/continuous-batching.md, projects/06-sovereign-ai-engine.md, projects/02-k8s-vllm-serving.md, notebooks/langgraph-two-call-extension.md]
updated: 2026-10-21
---

# LLM Evaluation

**One line:** four numbers decide whether a model is good enough to run —
quality, tail latency, throughput, and cost — and each is easy to measure
wrongly. These are the metrics the
[Sovereign AI blueprint](../../raw/roadmaps/2026-10-18-sovereign-ai-engine-blueprint.md) names.

## 1. Quality

- **Task metrics first** where ground truth exists: exact match, F1,
  build-success rate ([01](../projects/01-dockerfile-generator.md)), pass@k.
  Match the *final* answer, not the raw text. A reasoning model asked for "the number only"
  still wrote a worked solution ending in `\boxed{391}`. Whole-text matching fails that answer,
  and "any number in the text" passes on an intermediate step. The
  [gateway validator](../synthesis/2026-10-20-local-model-gateway-plan.md) reads the last
  `\boxed{}` value, else the last number
  ([journal](../../problem_first_ai/litellm/JOURNAL.md)).
- **Report a starved output budget as its own failure.** With a 16-token budget, a thinking
  model's Chat Completions and Responses API answers both came back empty (`finish_reason:
  length` / `status: incomplete`). That looks exactly like a broken model
  ([baseline](../../raw/story-updates/2026-10-21-local-model-gateway-baseline.md)).
- **Rubric + LLM-as-a-judge** for open-ended output. Write the rubric as
  concrete, scoreable criteria (e.g. correctness 0–3, completeness 0–3,
  actionability 0–2), and have the judge reason before scoring.
- **Pairwise** (candidate vs frontier baseline → win / tie / loss) is often
  more reliable than absolute scores for closing-the-gap work.
- **Judge biases** (Zheng et al., 2023): position (swap order and average),
  verbosity (penalise padding in the rubric), self-preference (don't let a
  model family judge itself). **Calibrate** on 30–50 human-labelled items and
  report agreement before trusting the judge.

The [generate → critique graph](../notebooks/langgraph-two-call-extension.md)
is a judge in miniature — its critique schema is a rubric.

## 2. Latency

| Metric | Meaning | Dominated by |
|---|---|---|
| TTFT | time to first token | queueing + prefill |
| TPOT / ITL | time per output token | decode, batch size |
| E2E | full response | TTFT + tokens × TPOT |

Report **P50 / P95 / P99** at a stated load. Use open-loop load (requests
arrive on a schedule, e.g. Poisson) for SLO numbers; closed-loop clients slow
down when the server does and hide tail latency (coordinated omission).

## 3. Throughput

Requests/s and output tokens/s **at the latency SLO** ("goodput"). Throughput
measured while P95 is blown is not capacity. Sweep concurrency to find the
knee ([continuous batching](continuous-batching.md),
[02](../projects/02-k8s-vllm-serving.md#evaluation--find-the-knee)).

Tools: `vllm bench serve`, GuideLLM, NVIDIA GenAI-Perf, k6 / Locust.

## 4. Cost

$/1k requests for the API; GPU-hours × rate + operations for self-hosting;
the volume where they cross is the
[crossover threshold](../projects/06-sovereign-ai-engine.md#crossover-analysis).

## Hygiene

- Freeze the eval set and the prompts; version both.
- Same decoding settings (temperature, max tokens) across candidates.
- Time one thing per number. Model load, the first call and steady-state calls are separate
  measurements; a "cold call" that includes a reply hides the load
  ([baseline](../../raw/story-updates/2026-10-21-local-model-gateway-baseline.md)).
- Every reported number goes into a `raw/story-updates/` note with how it was
  measured — that's what makes it citable here.
- Traces ([LLM tracing](llm-tracing.md)) give per-step latency and the exact
  prompts a judge should see; tag runs with a `thread_id` so evals and traces join up.

## Used by

[06](../projects/06-sovereign-ai-engine.md) · [02](../projects/02-k8s-vllm-serving.md) ·
[03](../projects/03-devops-aiops-platform.md) · [01](../projects/01-dockerfile-generator.md)

## Sources

- [Sovereign AI Engine blueprint](../../raw/roadmaps/2026-10-18-sovereign-ai-engine-blueprint.md) — quality rubrics / LLM-as-a-judge, P95/P99, throughput, crossover.
- [Local model gateway baseline (2026-10-21)](../../raw/story-updates/2026-10-21-local-model-gateway-baseline.md) — final-answer extraction, starved budgets, timing one thing per number.
- [Local model gateway journal](../../problem_first_ai/litellm/JOURNAL.md) — why the numeric check reads the final number.
- Background: Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena", 2023.
