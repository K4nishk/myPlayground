---
id: dockerfile-generator
title: An agent that writes Dockerfiles and proves them by building them
status: planned
projects: [wiki/projects/01-dockerfile-generator.md]
last_synced: 2026-10-18
evidence: []
---

# An agent that writes Dockerfiles and proves them by building them

> **One-liner:** A LangGraph agent turns a repo into a production-grade
> Dockerfile, using build logs — not the model — as the critic. Build-success
> rate: TBD.

## Situation
Every project in the infra roadmap ships containers, and hand-written
Dockerfiles drift from best practice: root users, unpinned base images, bloated
single-stage builds. LLMs can write Dockerfiles, but nothing guarantees they build.

## Task
Turn a repository into a Dockerfile that builds, starts, passes a health
check, and meets an image policy — verified by real tools, with a bounded
number of repair attempts.

## Action
*Planned* ([design](../../wiki/projects/01-dockerfile-generator.md)):
- Deterministic analyzer extracts a facts JSON (runtime, entrypoint, port,
  deps) so the model works from facts, not the raw repo.
- LangGraph generate → verify → repair loop; hadolint, BuildKit, smoke test and
  Trivy are the critic; repair is bounded (3 attempts) with full history in state.
- Image policy enforced by prompt *and* lint: multi-stage, digest-pinned base,
  non-root user, healthcheck.
- Built on the two-call pattern learned in the
  [LangGraph track](../../wiki/notebooks/langgraph-two-call-extension.md).

## Result
TBD — build success (first try / after repair) on a corpus of TBD repos;
image size vs hand-written reference; critical/high CVE delta.

## Talking points
- Tool-grounded critics beat LLM-only critics when an objective check exists.
- Facts-first prompting as a hallucination control.
- Why agent loops must be bounded and their history kept in state.

## Angles
- **Status update:** TBD after milestone 2 (generate + build loop).
- **Interview (STAR):** TBD — needs the corpus results.
- **Résumé bullet:** Built an LLM agent that generates and self-verifies Dockerfiles, reaching TBD% build success across TBD repos.

## Open threads
- Pick the corpus; record the baseline (hand-written) sizes and CVE counts.
- Decide frontier API vs sovereign model (link to project 06 eval set).

## Changelog
- 2026-10-18 — Seeded from the wiki design (planned).
