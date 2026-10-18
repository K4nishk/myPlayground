---
id: devops-aiops-platform
title: GitOps, LLM-serving golden signals, and an approval-gated triage agent
status: planned
projects: [wiki/projects/03-devops-aiops-platform.md]
last_synced: 2026-10-18
evidence: []
---

# GitOps, LLM-serving golden signals, and an approval-gated triage agent

> **One-liner:** An operating layer for the model-serving stack whose triage
> agent named the root cause in TBD of TBD replayed incidents.

## Situation
The serving stack spans GPUs, vLLM, KServe and KEDA. When something breaks,
the evidence is scattered across metrics, logs and recent deploys.

## Task
Make every change a commit, make LLM-specific health visible, and cut
time-to-diagnosis with an agent that is safe to give tool access to.

## Action
*Planned* ([design](../../wiki/projects/03-devops-aiops-platform.md)):
- Argo CD GitOps for all serving manifests.
- Golden signals adapted to LLMs: TTFT/TPOT percentiles, tokens/s, preemptions,
  KV-cache saturation, GPU-hours per million tokens.
- LangGraph triage agent on the classify → respond pattern: read-only tools by
  default, remediation behind a human-approval `interrupt`.

## Result
TBD — root-cause accuracy and time-to-summary on replayed/injected incidents
vs a human baseline.

## Talking points
- Adapting the four golden signals to token-streaming workloads.
- Designing agents with write access: least privilege, approval gates, traces.

## Angles
- **Status update:** TBD after milestone 2.
- **Interview (STAR):** TBD.
- **Résumé bullet:** Built an LLM incident-triage agent with approval-gated remediation; TBD% root-cause accuracy on TBD replayed incidents.

## Open threads
- Build the incident library (past or chaos-injected).

## Changelog
- 2026-10-18 — Seeded from the wiki design (planned).
