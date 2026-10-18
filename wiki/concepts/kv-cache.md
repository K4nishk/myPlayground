---
title: KV Cache
type: concept
status: draft
tags: [inference, memory, vllm, attention]
sources: [raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md, raw/roadmaps/2026-10-18-sovereign-ai-engine-blueprint.md]
related: [concepts/continuous-batching.md, concepts/quantization.md, projects/02-k8s-vllm-serving.md, projects/06-sovereign-ai-engine.md]
updated: 2026-10-18
---

# KV Cache

**One line:** during generation each new token attends to every previous
token. Caching their attention keys and values avoids recomputing them, and
that cache — not the weights — usually decides how many requests a GPU can
serve at once.

Called out as a core concept in the [roadmap](../../raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md)
and as one of the inference optimizations in the
[Sovereign AI blueprint](../../raw/roadmaps/2026-10-18-sovereign-ai-engine-blueprint.md).

## Sizing it

```
bytes per token = 2 (K and V) × layers × kv_heads × head_dim × bytes_per_value
```

_Illustrative_ small-model config — 28 layers, 8 KV heads, head dim 128, bf16 (2 bytes):

- per token: 2 × 28 × 8 × 128 × 2 = **112 KiB**
- one 8,192-token sequence: **~896 MiB**
- 32 such sequences: **~28 GiB** — more than the ~6 GB of bf16 weights a 3B model needs.

So on a 24 GB GPU at `--gpu-memory-utilization=0.90`, after ~6 GB of weights
and activation overhead, roughly 14 GB is left for KV — about 15 full-length
8k sequences, or many more short ones. This is why `--max-model-len` and
request length distribution dominate capacity planning
([02 knobs](../projects/02-k8s-vllm-serving.md#the-knobs-that-matter)).

## What shrinks it

| Technique | Effect |
|---|---|
| Grouped-query / multi-query attention (model architecture) | KV size ÷ (query heads / KV heads) |
| FP8 KV cache (`--kv-cache-dtype fp8`) | ~½ the bytes; small quality risk — evaluate ([quantization](quantization.md)) |
| Shorter `--max-model-len` | Caps worst-case per-request footprint |
| Prefix caching | Shared prompt prefixes (system prompts, few-shot examples) stored once |

## PagedAttention

vLLM stores KV in fixed-size **blocks** allocated on demand rather than one
contiguous max-length slab per request (Kwon et al., SOSP 2023). Near-zero
fragmentation means many more concurrent sequences fit, and blocks can be
shared between requests with the same prefix. It is what makes
[continuous batching](continuous-batching.md) pay off.

## When it runs out

KV-cache usage near 100% → the scheduler **preempts** sequences (recompute or
swap), latency spikes, throughput drops. Watch the KV-usage metric next to
`num_requests_waiting`; both are better autoscaling signals than GPU
utilization ([04](../projects/04-kserve-gpu-autoscaling.md)).

## Used by

[02 vLLM serving](../projects/02-k8s-vllm-serving.md) ·
[04 KServe autoscaling](../projects/04-kserve-gpu-autoscaling.md) ·
[06 Sovereign AI Engine](../projects/06-sovereign-ai-engine.md)

## Sources

- [AI infra project roadmap](../../raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md) — named as a core concept.
- [Sovereign AI Engine blueprint](../../raw/roadmaps/2026-10-18-sovereign-ai-engine-blueprint.md) — KV caching as an inference optimization.
- Background: Kwon et al., "Efficient Memory Management for Large Language Model Serving with PagedAttention", SOSP 2023.
