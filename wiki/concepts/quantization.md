---
title: Weight Quantization
type: concept
status: draft
tags: [quantization, memory, inference, precision]
sources: [raw/roadmaps/2026-10-18-sovereign-ai-engine-blueprint.md]
related: [concepts/kv-cache.md, concepts/parameter-efficient-finetuning.md, concepts/llm-evaluation.md, projects/06-sovereign-ai-engine.md]
updated: 2026-10-18
---

# Weight Quantization

**One line:** store weights in fewer bits to cut memory and often raise
throughput, at a precision cost you must measure — optimization #2 in the
[Sovereign AI blueprint](../../raw/roadmaps/2026-10-18-sovereign-ai-engine-blueprint.md),
which asks specifically for the precision-vs-performance trade-off.

## Memory arithmetic

`weight memory ≈ parameters × bits / 8` (plus a few % for scales/zero-points;
embeddings and the output head are often kept at higher precision).

| 3B parameters (_illustrative_) | Weights |
|---|---|
| bf16 / fp16 | ~6 GB |
| FP8 / INT8 | ~3 GB |
| INT4 | ~1.5 GB |

Freed memory becomes [KV cache](kv-cache.md) — i.e. more concurrent requests —
or lets a model fit a smaller GPU / MIG slice.

## Methods

| Method | Kind | Notes |
|---|---|---|
| FP8 (W8A8) | Weights + activations | Needs recent GPUs for native speedup; usually smallest quality loss |
| INT8 weight-only / W8A8 (SmoothQuant-style) | 8-bit | Broad hardware support |
| GPTQ | 4-bit weight-only, post-training | Layer-wise error-compensating; needs calibration data |
| AWQ | 4-bit weight-only, post-training | Protects activation-salient channels; needs calibration data |
| GGUF k-quants | 2–8-bit, llama.cpp | CPU / laptop / edge deployments |
| NF4 (bitsandbytes) | 4-bit | Built for QLoRA training ([PEFT](parameter-efficient-finetuning.md)), not the fastest for serving |

Separate knob: **KV-cache quantization** (`--kv-cache-dtype fp8`) — shrinks
the cache, not the weights.

## Evaluating the trade-off

- Same eval set and judge as every other phase ([evaluation](llm-evaluation.md)).
- Compare **distributions, not just means** — INT4 can match on average and
  fail badly on a tail of hard items. Inspect the worst 10%.
- Measure throughput and P95/P99 at the *same concurrency*: weight-only INT4
  speeds up memory-bound decode, but dequantization overhead can hurt
  compute-bound prefill at high batch sizes.
- Calibration data should resemble production prompts.

Output: a chart of quality vs VRAM vs tokens/s per precision — phase 4 of
[project 06](../projects/06-sovereign-ai-engine.md#phases).

## Used by

[06 Sovereign AI Engine](../projects/06-sovereign-ai-engine.md) ·
[02 vLLM serving](../projects/02-k8s-vllm-serving.md) ·
[05 scale-to-zero](../projects/05-keda-scale-to-zero.md) (smaller weights load faster)

## Sources

- [Sovereign AI Engine blueprint](../../raw/roadmaps/2026-10-18-sovereign-ai-engine-blueprint.md) — weight quantization as optimization #2.
- Background: Frantar et al., "GPTQ", 2022; Lin et al., "AWQ", 2023; Xiao et al., "SmoothQuant", 2022.
