# Wiki index

Catalog of every page. The agent reads this first on every query and updates
it on every ingest. Rules: [WIKI_SCHEMA.md](WIKI_SCHEMA.md) · History: [log.md](log.md) ·
Narratives: [story bank](../story-bank/index.md).

## Overview

| Page | Summary | Status | Updated |
|---|---|---|---|
| [Overview](overview.md) | How the six projects and two tracks (LangGraph learning, local model gateway) connect: dependency graph, the measurement chain, concept map; gateway first slice measured | draft | 2026-10-21 |

## Projects

| Page | Summary | Status | Updated |
|---|---|---|---|
| [01 Dockerfile Generator](projects/01-dockerfile-generator.md) | LangGraph agent that writes Dockerfiles and verifies them with build/lint/scan as the critic | draft | 2026-10-18 |
| [02 Kubernetes vLLM Serving](projects/02-k8s-vllm-serving.md) | vLLM on a GPU node pool: manifest, the knobs that matter, metrics, finding the concurrency knee | draft | 2026-10-18 |
| [03 DevOps / AIOps Platform](projects/03-devops-aiops-platform.md) | GitOps delivery, LLM golden signals, and an approval-gated classify→respond triage agent | draft | 2026-10-18 |
| [04 KServe GPU Autoscaling](projects/04-kserve-gpu-autoscaling.md) | Autoscale on concurrency/queue depth, not GPU util; two-level pod + node scaling; scaleTarget from the knee | draft | 2026-10-18 |
| [05 KEDA Scale-to-Zero](projects/05-keda-scale-to-zero.md) | Activation outside the pod, ScaledObject with two triggers, cold-start budget, hot/warm/cold tiers | draft | 2026-10-18 |
| [06 Sovereign AI Engine](projects/06-sovereign-ai-engine.md) | Aish's framework: frontier baseline → 2–4B open model + PEFT + quantization + batching → crossover decision; conflict with the gateway plan's dev loop open | draft | 2026-10-20 |

## Concepts

| Page | Summary | Status | Updated |
|---|---|---|---|
| [KV cache](concepts/kv-cache.md) | Sizing formula, why it — not weights — caps concurrency, PagedAttention, what shrinks it | draft | 2026-10-18 |
| [Continuous batching](concepts/continuous-batching.md) | Iteration-level scheduling, prefill vs decode, chunked prefill, the concurrency knee | draft | 2026-10-18 |
| [GPU scheduling](concepts/gpu-scheduling.md) | Device plugin, taints/affinity, MIG vs time-slicing vs MPS, DRA, queueing, warm-node tricks | draft | 2026-10-18 |
| [Cold starts](concepts/cold-starts.md) | The five terms of an LLM cold start, how to measure each, mitigations; measured Ollama reloads (0.8 s, but about 5 s slower within 2 s of an unload) | draft | 2026-10-21 |
| [PEFT (LoRA / QLoRA)](concepts/parameter-efficient-finetuning.md) | LoRA math and knobs, QLoRA, merge vs multi-LoRA serving, running sweeps well | draft | 2026-10-18 |
| [Quantization](concepts/quantization.md) | Memory arithmetic, FP8/INT8/GPTQ/AWQ/GGUF/NF4, evaluating the precision trade-off | draft | 2026-10-18 |
| [LLM evaluation](concepts/llm-evaluation.md) | Quality (rubrics, LLM-judge biases, final-answer matching, starved budgets), TTFT/TPOT/E2E percentiles, goodput, cost | draft | 2026-10-21 |
| [LangGraph state graphs](concepts/langgraph-state-graphs.md) | State, reducers, nodes, edges, checkpointers, streaming modes, interrupts, plus 10 verified gotchas (LangGraph 1.2) | draft | 2026-10-18 |
| [LLM tracing](concepts/llm-tracing.md) | OpenTelemetry + OpenInference + Arize: span tree of a graph run, thread_id → session, flush and re-run gotchas | draft | 2026-10-18 |

## Notebooks

| Page | Summary | Status | Updated |
|---|---|---|---|
| [Notebook review: LangChain & LangGraph Demo](notebooks/langchain-langgraph-demo.md) | Your Problem-First AI notebook: what it covers, the fixes to make first (key prefixes in a public repo, wrong kernel, fragile router), smaller issues | active | 2026-10-20 |
| [LangGraph two-call extension](notebooks/langgraph-two-call-extension.md) | 7 steps built on your notebook's cells: offline harness, hardened router, generate→critique, trace handling, bounded loop, concurrency, sovereign A/B; companion notebook runs offline | active | 2026-10-18 |

## Synthesis

Answers to queries worth keeping land in `synthesis/` and are listed here.

| Page | Summary | Status | Updated |
|---|---|---|---|
| [Local model gateway plan (2026-10-20)](synthesis/2026-10-20-local-model-gateway-plan.md) | LiteLLM front door with local / cluster / frontier tiers; aliases promise a role; Mac is the dev loop. First slice built and measured: 4/4 cases, about 14.8 tok/s, 8.23 GiB on the GPU, no swap | active | 2026-10-21 |
