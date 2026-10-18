---
id: k8s-vllm-serving
title: Serving open-weight LLMs on Kubernetes, sized by measurement
status: planned
projects: [wiki/projects/02-k8s-vllm-serving.md]
last_synced: 2026-10-18
evidence: []
---

# Serving open-weight LLMs on Kubernetes, sized by measurement

> **One-liner:** vLLM on a GPU node pool with full observability, and a
> concurrency sweep that found the knee at TBD concurrent requests per GPU.

## Situation
Running models privately needs a serving layer that is observable and whose
capacity is measured rather than guessed — every later project (autoscaling,
scale-to-zero, the sovereign engine) depends on that number.

## Task
Serve a 2–4B open-weight model through vLLM's OpenAI-compatible API on
Kubernetes, instrument it, and find the per-replica concurrency at which
latency falls off a cliff.

## Action
*Planned* ([design](../../wiki/projects/02-k8s-vllm-serving.md)):
- Tainted GPU node pool managed by the NVIDIA GPU Operator.
- vLLM Deployment with a long startup probe and a persistent model cache.
- Prometheus + Grafana on vLLM queue, KV-cache and latency histograms plus DCGM.
- Concurrency sweep to locate the knee; repeat with a quantized variant.

## Result
TBD — knee concurrency; P95 TTFT and output tokens/s at the knee; KV-cache
usage at saturation.

## Talking points
- The KV cache, not the weights, limits concurrency
  ([KV cache](../../wiki/concepts/kv-cache.md)).
- Startup probes for multi-minute model loads.
- Why the knee becomes the autoscaling target in project 04.

## Angles
- **Status update:** TBD after milestone 1.
- **Interview (STAR):** TBD — needs the sweep numbers.
- **Résumé bullet:** Deployed vLLM on Kubernetes GPU nodes with Prometheus observability; load testing set a TBD-request/GPU capacity target used for autoscaling.

## Open threads
- Choose model and GPU type; record both in the first story update.

## Changelog
- 2026-10-18 — Seeded from the wiki design (planned).
