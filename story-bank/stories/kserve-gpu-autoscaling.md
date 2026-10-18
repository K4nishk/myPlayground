---
id: kserve-gpu-autoscaling
title: Autoscaling GPU inference on the signal users actually feel
status: planned
projects: [wiki/projects/04-kserve-gpu-autoscaling.md]
last_synced: 2026-10-18
evidence: []
---

# Autoscaling GPU inference on the signal users actually feel

> **One-liner:** KServe autoscaling on concurrency and queue depth instead of
> GPU utilization, recovering the latency SLO TBD× faster under step load.

## Situation
Provisioning GPUs for peak wastes GPU-hours, and default CPU-based autoscaling
can't see GPU saturation. GPU utilization pins near 100% long before vLLM runs
out of batch capacity.

## Task
Scale model replicas — and GPU nodes — on signals that track user latency,
with targets derived from measured capacity.

## Action
*Planned* ([design](../../wiki/projects/04-kserve-gpu-autoscaling.md)):
- KServe InferenceService with `scaleTarget` set from the project 02 knee.
- Head-to-head: concurrency vs waiting-queue vs GPU-utilization scaling.
- GPU node-pool autoscaling end to end; warm-node vs cold-node comparison.

## Result
TBD — time to recover P95 under step load per metric; GPU-hours vs fixed
peak provisioning over a daily curve.

## Talking points
- Two-level scaling (pods need nodes) and where the time goes.
- Why GPU utilization % is a misleading scaling signal.

## Angles
- **Status update:** TBD.
- **Interview (STAR):** TBD.
- **Résumé bullet:** Autoscaled KServe GPU inference on queue depth, cutting GPU-hours TBD% vs fixed provisioning while holding P95 SLO.

## Open threads
- Depends on the project 02 knee measurement.

## Changelog
- 2026-10-18 — Seeded from the wiki design (planned).
