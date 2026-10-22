# Wiki index

Catalog of every page. The agent reads this first on every query and updates
it on every ingest. Rules: [WIKI_SCHEMA.md](WIKI_SCHEMA.md) · History: [log.md](log.md) ·
Narratives: [story bank](../story-bank/index.md).

## Overview

| Page | Summary | Status | Updated |
|---|---|---|---|
| [Overview](overview.md) | How the six projects connect: dependency graph, the measurement chain, concept map | draft | 2026-10-18 |

## Projects

| Page | Summary | Status | Updated |
|---|---|---|---|
| [01 Dockerfile Generator](projects/01-dockerfile-generator.md) | LangGraph agent that writes Dockerfiles and verifies them with build/lint/scan as the critic | draft | 2026-10-18 |
| [02 Kubernetes vLLM Serving](projects/02-k8s-vllm-serving.md) | vLLM on a GPU node pool: manifest, the knobs that matter, metrics, finding the concurrency knee | draft | 2026-10-18 |
| [03 DevOps / AIOps Platform](projects/03-devops-aiops-platform.md) | GitOps delivery, LLM golden signals, and an approval-gated classify→respond triage agent | draft | 2026-10-18 |
| [04 KServe GPU Autoscaling](projects/04-kserve-gpu-autoscaling.md) | Autoscale on concurrency/queue depth, not GPU util; two-level pod + node scaling; scaleTarget from the knee | draft | 2026-10-18 |
| [05 KEDA Scale-to-Zero](projects/05-keda-scale-to-zero.md) | Activation outside the pod, ScaledObject with two triggers, cold-start budget, hot/warm/cold tiers | draft | 2026-10-18 |
| [06 Sovereign AI Engine](projects/06-sovereign-ai-engine.md) | Aish's framework: frontier baseline → 2–4B open model + PEFT + quantization + batching → crossover decision | draft | 2026-10-18 |

## Concepts

| Page | Summary | Status | Updated |
|---|---|---|---|
| [KV cache](concepts/kv-cache.md) | Sizing formula, why it — not weights — caps concurrency, PagedAttention, what shrinks it | draft | 2026-10-18 |
| [Continuous batching](concepts/continuous-batching.md) | Iteration-level scheduling, prefill vs decode, chunked prefill, the concurrency knee | draft | 2026-10-18 |
| [GPU scheduling](concepts/gpu-scheduling.md) | Device plugin, taints/affinity, MIG vs time-slicing vs MPS, DRA, queueing, warm-node tricks | draft | 2026-10-18 |
| [Cold starts](concepts/cold-starts.md) | The five terms of an LLM cold start, how to measure each, mitigations | draft | 2026-10-18 |
| [PEFT (LoRA / QLoRA)](concepts/parameter-efficient-finetuning.md) | LoRA math and knobs, QLoRA, merge vs multi-LoRA serving, running sweeps well | draft | 2026-10-18 |
| [Quantization](concepts/quantization.md) | Memory arithmetic, FP8/INT8/GPTQ/AWQ/GGUF/NF4, evaluating the precision trade-off | draft | 2026-10-18 |
| [LLM evaluation](concepts/llm-evaluation.md) | Quality (rubrics, LLM-judge biases), TTFT/TPOT/E2E percentiles, goodput, cost | draft | 2026-10-18 |
| [LangGraph state graphs](concepts/langgraph-state-graphs.md) | State, reducers, nodes, edges, checkpointers, streaming modes, interrupts (LangGraph 1.x) | draft | 2026-10-18 |

## Notebooks

| Page | Summary | Status | Updated |
|---|---|---|---|
| [LangGraph two-call extension](notebooks/langgraph-two-call-extension.md) | Step-by-step plan + tested code: generate→critique, reflection loop, classify→respond, trace handling | active | 2026-10-18 |

## Synthesis

Answers to queries worth keeping land in `synthesis/` and are listed here.

| Page | Summary | Status | Updated |
|---|---|---|---|
| _none yet_ | | | |
