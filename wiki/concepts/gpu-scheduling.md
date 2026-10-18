---
title: GPU Scheduling on Kubernetes
type: concept
status: draft
tags: [kubernetes, gpu, scheduling, nvidia]
sources: [raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md]
related: [concepts/cold-starts.md, projects/02-k8s-vllm-serving.md, projects/04-kserve-gpu-autoscaling.md, projects/05-keda-scale-to-zero.md]
updated: 2026-10-18
---

# GPU Scheduling on Kubernetes

**One line:** GPUs are scarce, indivisible-by-default, expensive resources;
scheduling is about putting the right pods on them, keeping everything else
off them, and having one free when autoscaling asks.

Named as a core concept in the [roadmap](../../raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md).

## Basics

- The **NVIDIA device plugin** (installed by the GPU Operator) advertises
  `nvidia.com/gpu` on each node. Requests are whole integers, set as limits
  (requests default to limits), and are never overcommitted.
- **Keep other pods off:** taint GPU nodes (`nvidia.com/gpu:NoSchedule`) and
  give GPU workloads a matching toleration.
- **Pick the right GPU:** GPU Feature Discovery labels nodes with product,
  memory, and driver details; use node affinity to target them.
- **Topology:** tensor-parallel replicas want GPUs on one node with fast
  interconnect; request them together in one pod.

## Sharing one GPU

| Mechanism | Isolation | Use for |
|---|---|---|
| MIG (Multi-Instance GPU, data-center GPUs) | Hardware: memory + compute partitions | Several small models with guaranteed slices |
| Time-slicing | None for memory; context switches | Dev/test, bursty low-traffic models |
| MPS | Shared contexts, limited memory isolation | Many small concurrent kernels |

For a 2–4B model ([06](../projects/06-sovereign-ai-engine.md)) a MIG slice
can be enough — a cost lever worth testing.

## Beyond the device plugin

- **Dynamic Resource Allocation (DRA)** — richer device requests (attributes,
  sharing, partitions) through ResourceClaims; core DRA reached GA in
  Kubernetes 1.34. Expect GPU drivers to move toward it.
- **Queueing and gang scheduling** for training/fine-tuning jobs: Kueue or
  Volcano, so a multi-GPU LoRA job starts all-or-nothing.
- **Node autoscaling:** Cluster Autoscaler or Karpenter with a dedicated GPU
  node pool. A pending GPU pod is what triggers a new node — the largest
  [cold-start](cold-starts.md) term.
- **Headroom trick:** low-priority placeholder pods hold a warm GPU node; real
  workloads preempt them instantly.

## Used by

[02](../projects/02-k8s-vllm-serving.md) · [04](../projects/04-kserve-gpu-autoscaling.md) ·
[05](../projects/05-keda-scale-to-zero.md) · [06](../projects/06-sovereign-ai-engine.md)

## Sources

- [AI infra project roadmap](../../raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md) — named as a core concept.
