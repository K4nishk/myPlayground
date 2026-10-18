---
title: Continuous Batching
type: concept
status: draft
tags: [inference, throughput, latency, vllm, scheduling]
sources: [raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md, raw/roadmaps/2026-10-18-sovereign-ai-engine-blueprint.md]
related: [concepts/kv-cache.md, concepts/llm-evaluation.md, projects/02-k8s-vllm-serving.md, projects/06-sovereign-ai-engine.md]
updated: 2026-10-18
---

# Continuous Batching

**One line:** schedule the batch every decode step instead of every request —
finished sequences leave and waiting ones join immediately, so the GPU never
idles waiting for the longest response in a batch.

Named in the [roadmap](../../raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md)
and the [Sovereign AI blueprint](../../raw/roadmaps/2026-10-18-sovereign-ai-engine-blueprint.md)
as the route to high concurrency.

## Static vs continuous

```
static:      [A A A A A A A A]  B, C finish early but wait for A;
             [B B B . . . . .]  new request D waits for the whole batch
             [C C . . . . . .]

continuous:  [A A A A A A A A]
             [B B B D D D D E]  D joins the step after B finishes,
             [C C F F F F F F]  F the step after C
```

Iteration-level scheduling was introduced by Orca (Yu et al., OSDI 2022);
vLLM combines it with paged [KV cache](kv-cache.md) allocation so the batch
can grow as long as KV blocks are free.

## Two phases, two bottlenecks

- **Prefill** (process the prompt): compute-bound, many tokens at once. Drives
  time-to-first-token (TTFT).
- **Decode** (one token per step per sequence): memory-bandwidth-bound. Drives
  time per output token. Batching decode steps is nearly free up to a point,
  which is where the throughput gain comes from.
- **Chunked prefill** splits long prompts across steps so a big prefill doesn't
  stall everyone's decode.

## The trade-off you tune

More sequences per step → more tokens/s overall, but each request's
per-token latency rises and, once KV is full, preemption kicks in. The
concurrency **knee** (throughput flattens, P95 climbs) is the operating point
— measure it ([02 evaluation](../projects/02-k8s-vllm-serving.md#evaluation--find-the-knee))
and autoscale on it ([04](../projects/04-kserve-gpu-autoscaling.md)).

vLLM knobs: `--max-num-seqs` (sequences per step), `--max-num-batched-tokens`
(token budget per step), chunked-prefill settings.

## Used by

[02 vLLM serving](../projects/02-k8s-vllm-serving.md) ·
[04 KServe autoscaling](../projects/04-kserve-gpu-autoscaling.md) ·
[06 Sovereign AI Engine](../projects/06-sovereign-ai-engine.md)

## Sources

- [AI infra project roadmap](../../raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md) — named as a core concept.
- [Sovereign AI Engine blueprint](../../raw/roadmaps/2026-10-18-sovereign-ai-engine-blueprint.md) — continuous batching for high concurrency.
- Background: Yu et al., "Orca: A Distributed Serving System for Transformer-Based Generative Models", OSDI 2022.
