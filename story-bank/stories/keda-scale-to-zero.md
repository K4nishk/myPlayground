---
id: keda-scale-to-zero
title: Scale-to-zero for GPU models with a cold-start budget
status: planned
projects: [wiki/projects/05-keda-scale-to-zero.md]
last_synced: 2026-10-18
evidence: []
---

# Scale-to-zero for GPU models with a cold-start budget

> **One-liner:** Idle models cost zero GPU-hours; the first request after idle
> is served in TBD s, down from TBD s after cold-start mitigations.

## Situation
Many models are idle most of the day yet each holds a GPU. Scaling to zero
saves that cost — but LLM cold starts take minutes, not milliseconds.

## Task
Scale to zero without losing requests, and bring the cold path inside an
agreed budget per traffic tier.

## Action
*Planned* ([design](../../wiki/projects/05-keda-scale-to-zero.md)):
- KEDA with an activation signal outside the model pod (HTTP add-on or
  gateway metric) for 0 → 1, and vLLM queue depth for 1 → N.
- Cold start broken into node, pull, load and init terms, measured per tier
  ([cold starts](../../wiki/concepts/cold-starts.md)).
- Mitigations: pre-pulled images, node-local weight cache, quantized weights.

## Result
TBD — per-term cold-start times before/after; idle GPU-hours eliminated.

## Talking points
- The activation chicken-and-egg problem at zero replicas.
- Hot / warm / cold tiers as a cost-vs-latency product decision.

## Angles
- **Status update:** TBD.
- **Interview (STAR):** TBD.
- **Résumé bullet:** Implemented KEDA scale-to-zero for GPU model serving, eliminating TBD idle GPU-hours/month with a TBD-second cold-start budget.

## Open threads
- Pick the traffic pattern to model (bursty daily curve).

## Changelog
- 2026-10-18 — Seeded from the wiki design (planned).
