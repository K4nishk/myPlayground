---
title: Parameter-Efficient Fine-Tuning (LoRA / QLoRA)
type: concept
status: draft
tags: [fine-tuning, peft, lora, qlora, training]
sources: [raw/roadmaps/2026-10-18-sovereign-ai-engine-blueprint.md, raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md]
related: [concepts/quantization.md, concepts/llm-evaluation.md, projects/06-sovereign-ai-engine.md]
updated: 2026-10-18
---

# Parameter-Efficient Fine-Tuning (LoRA / QLoRA)

**One line:** freeze the base model and train a tiny set of added weights, so a
small open model can be specialised on one GPU — optimization #1 in the
[Sovereign AI blueprint](../../raw/roadmaps/2026-10-18-sovereign-ai-engine-blueprint.md).

## LoRA

For a frozen weight matrix `W₀ (d × k)`, learn a low-rank update:

```
W = W₀ + (α / r) · B · A        A: r × k,  B: d × r,  r ≪ min(d, k)
```

- `B` starts at zero, so training starts from the base model's behaviour.
- Trainable parameters per adapted matrix: `r · (d + k)`.
  _Illustrative:_ d = k = 3072, r = 16 → ~98k vs ~9.4M for the full matrix (~1%).
- **Knobs:** rank `r` (capacity), `α` (scale; α = r or 2r are common starting
  points), `target_modules` (attention projections only, or also the MLP —
  MLP usually helps on knowledge-heavy tasks), dropout, learning rate (higher
  than full fine-tuning).

## QLoRA

Dettmers et al., 2023: keep the frozen base in **4-bit NormalFloat (NF4)**,
train LoRA adapters in 16-bit on top. Adds double quantization (quantize the
quantization constants) and paged optimizers to survive memory spikes. Net
effect: fine-tuning memory drops by roughly the weight-quantization factor, so
2–4B models fit comfortably on a single consumer GPU.

## Serving the result

| Option | How | Trade-off |
|---|---|---|
| Merge | Fold `BA` into `W₀`, ship one model | No runtime overhead; one copy of weights per task |
| Multi-LoRA serving | vLLM `--enable-lora`, adapters selected per request | Many tasks on one base; small per-request overhead |

For QLoRA, merge into the **16-bit** base, then re-quantize for serving with a
serving-grade method ([quantization](quantization.md)) — and evaluate *after*
re-quantization, since the two steps interact.

## How to run it well ([06 phase 3](../projects/06-sovereign-ai-engine.md#phases))

- Hold out the eval set **before** building training data; dedupe against it.
- Sweep `r ∈ {8, 16, 32}` and target modules; plot quality vs trainable params.
- Track the gap to the frontier baseline per run
  ([evaluation](llm-evaluation.md)), plus GPU-hours per run — training cost
  belongs in the crossover's `ops_month`.

Tooling: Hugging Face PEFT + TRL (`SFTTrainer`), bitsandbytes for 4-bit;
Unsloth-style kernels for faster single-GPU runs.

## Used by

[06 Sovereign AI Engine](../projects/06-sovereign-ai-engine.md) ·
[02 vLLM serving](../projects/02-k8s-vllm-serving.md) (multi-LoRA)

## Sources

- [Sovereign AI Engine blueprint](../../raw/roadmaps/2026-10-18-sovereign-ai-engine-blueprint.md) — PEFT with LoRA/QLoRA as optimization #1.
- [AI infra project roadmap](../../raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md) — named as a core concept.
- Background: Hu et al., "LoRA: Low-Rank Adaptation of Large Language Models", 2021; Dettmers et al., "QLoRA: Efficient Finetuning of Quantized LLMs", 2023.
