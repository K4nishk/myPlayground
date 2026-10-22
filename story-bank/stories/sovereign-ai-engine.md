---
id: sovereign-ai-engine
title: When does running your own model beat renting a frontier API?
status: planned
projects: [wiki/projects/06-sovereign-ai-engine.md]
last_synced: 2026-10-18
evidence: []
---

# When does running your own model beat renting a frontier API?

> **One-liner:** A 2–4B open-weight model, tuned with QLoRA, quantized and
> served with continuous batching, closed the quality gap to a frontier API
> from TBD% to TBD%, with a cost crossover at TBD requests/month.

Framework credit: **Aish** (Sovereign AI Engine blueprint).

## Situation
Frontier APIs are the default, but their cost grows linearly with volume and
the data leaves your boundary. Whether a small private model is good enough —
and at what volume it is cheaper — is usually argued, not measured.

## Task
Following Aish's framework: baseline a frontier API, measure the gap to open
models in the 2–4B range, close it with PEFT, quantization and inference
optimization, and decide with quality, P95/P99, throughput and the volume
crossover ([blueprint](../../raw/roadmaps/2026-10-18-sovereign-ai-engine-blueprint.md)).

## Action
*Planned* ([design](../../wiki/projects/06-sovereign-ai-engine.md)):
- Fixed eval set + rubric; LLM judge calibrated on human labels.
- Phases: frontier baseline → zero-shot open models → LoRA/QLoRA → quantization
  → vLLM serving sweep → crossover memo.
- Crossover from measured capacity at SLO, not peak throughput
  ([calculator](../../labs/sovereign-ai/crossover.py)).

## Result
TBD — gap at each stage; P95/P99 at target concurrency; sustained req/s per
GPU; VRAM per precision; crossover volume and the go/no-go.

## Talking points
- Quality bar first, cost second: the decision rule.
- Where quantization hurts (tails, not means).
- Hidden costs in self-hosting: engineering time, re-tuning, idle GPUs.
- Sovereignty as a non-cost driver (residency, privacy, lock-in).

## Angles
- **Status update:** TBD after phase 1 (frontier baseline).
- **Interview (STAR):** TBD — the strongest version tells the gap shrinking stage by stage.
- **Résumé bullet:** Benchmarked and optimized a 2–4B open-weight model (QLoRA, INT4, continuous batching) against a frontier API; closed the quality gap to TBD% and identified a TBD-request/month cost crossover.

## Open threads
- Choose the task(s) and build the eval set (phase 0).
- Confirm with Aish how they want the framework credited in public write-ups.

## Changelog
- 2026-10-18 — Seeded from Aish's blueprint and the wiki design (planned).
