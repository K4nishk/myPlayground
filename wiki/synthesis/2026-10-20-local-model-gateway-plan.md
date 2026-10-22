---
title: Local Model Gateway — Plan (2026-10-20)
type: synthesis
status: active
tags: [litellm, gateway, ollama, open-weight, routing, sovereign-ai]
sources: [raw/inbox/2026-10-20-local-model-gateway-decisions.md, raw/story-updates/2026-10-21-local-model-gateway-baseline.md, problem_first_ai/litellm/JOURNAL.md]
related: [projects/06-sovereign-ai-engine.md, overview.md, concepts/cold-starts.md, concepts/llm-evaluation.md]
updated: 2026-10-21
---

# Local Model Gateway — Plan

A LiteLLM gateway is the routing layer between a frontier API and open-weight models, built in the
direction of [project 06](../projects/06-sovereign-ai-engine.md) (Aish's Sovereign AI Engine
framework). You decided this in a design session on 2026-10-20
([decisions note](../../raw/inbox/2026-10-20-local-model-gateway-decisions.md)). It has two
reasons: to learn LiteLLM, and to run coursework against models other than `gpt-6-luna`.

The vocabulary (gateway, alias, role, tier, candidate, baseline…) is defined in the project's
[GLOSSARY](../../problem_first_ai/litellm/GLOSSARY.md). The two hard-to-reverse decisions are
recorded as ADRs in [`docs/adr/`](../../problem_first_ai/litellm/docs/adr/).

```mermaid
flowchart LR
  C[client<br/>Chat Completions · Responses API] --> G[LiteLLM gateway<br/>127.0.0.1:4000]
  G -->|local-reasoning| L[local · this Mac<br/>Ollama · deepseek-r1:14b]
  G -.->|Planned| K[cluster · Kubernetes<br/>own NVIDIA GPUs]
  G -.->|Planned| F[frontier · vendor API<br/>gpt-6-luna]
```

## Tiers and aliases

| Tier | Runs on | Its job |
|---|---|---|
| `local` | This Mac (M3 Pro, 18 GB): Ollama now, vllm-metal later | The dev loop: aliases, cases and the gateway are built and checked here |
| `cluster` | Kubernetes on your own NVIDIA hardware | Where capacity and resource utilization are measured |
| `frontier` | A vendor API (`gpt-6-luna`) | The baseline. Its alias is *Planned* |

The tier split is [ADR 0001](../../problem_first_ai/litellm/docs/adr/0001-mac-is-the-dev-loop.md).
It narrows the Mac's role; it doesn't replace the Kubernetes stack from projects 02–05.

Aliases are named `<tier>-<role>`, where the role is reasoning, text or coding.
[ADR 0002](../../problem_first_ai/litellm/docs/adr/0002-an-alias-promises-a-role.md) says an alias
**promises a role, not a model**, so it can be re-pointed (for example from Ollama to vllm-metal).
Three rules follow:

- Every run records the backend model behind each alias.
- Baselines are keyed by alias plus backend model, and re-pointing an alias starts a new baseline.
- Experiments use *candidates*: aliases pinned to one backend model and never re-pointed.

A baseline is a passing run recorded as a dated `raw/story-updates/` note. That is the only way its
numbers can be cited here.

## Decided

- **First slice** (built 2026-10-20/21; results below):
  - One alias, `local-reasoning` → `deepseek-r1:14b` on Ollama 0.40.6.
  - A 4096-token context window, with one model resident at a time.
  - The gateway on `127.0.0.1:4000`, serving both Chat Completions and the Responses API.
  - An end-to-end validator skill that every later change must pass.
- **`deepseek-r1:14b` cannot call tools.** Its Ollama prompt template has no tools section. It can
  serve Assignment 1's query-understanding part, but not the tool or ReAct parts.
- **Supply chain.** LiteLLM is pinned to an exact version with a lockfile: 1.103.3, the newest
  release at least 14 days old. The note's reason is that releases 1.82.7 and 1.82.8 were
  compromised on PyPI in March 2026.
- **Keys.** No key value is written to any file. Only frontier aliases read a key, and they read it
  from the environment.
- **Course material is never published.** `problem_first_ai/preread/` and
  `problem_first_ai/Assignment 1/` stay out of git. This is now enforced in `.gitignore`.

## Built and measured (2026-10-21)

All figures are from the
[baseline note](../../raw/story-updates/2026-10-21-local-model-gateway-baseline.md): three
consecutive runs of the validator through the gateway, at temperature 0, on the M3 Pro.

| Case | API | Latency | Output tokens | Tokens/s |
|---|---|---|---|---|
| Arithmetic | Chat Completions | 17.17–17.26 s | 255 | 14.8 |
| Riddle | Chat Completions | 20.78–20.79 s | 309 | 14.9 |
| Arithmetic | Responses API | 13.06–13.11 s | 193 | 14.7–14.8 |
| Course settings (`reasoning_effort: low`) | Responses API | 14.63–14.68 s | 217 | 14.8 |

- **Every case passed in every run, with no swapping.**
- **The model** takes 8.23 GiB, all on the GPU, with a 4096-token context window.
- **Load time** is 0.78–0.79 s, timed directly on Ollama 5 s after an unload.
- **The opening call** through the gateway takes 1.16–1.19 s.
- **The course app's call settings pass through the gateway.** The Responses API with
  `reasoning_effort: low` reaches the local model through LiteLLM's conversion.
- **A reload straight after an unload is slow.** Within 2 s of an unload a load took 5.1–6.4 s;
  from 5 s on, about 0.8 s. That's why the validator waits 5 s before timing a load. Why the wait
  matters is still a hypothesis
  ([cold starts](../concepts/cold-starts.md#measured-reloading-a-model-on-ollama-apple-silicon)).

**How the validator works** (`problem_first_ai/litellm/validator/`, run by the
`local-model-e2e-validator` skill). For each alias it:
1. loads the model on Ollama (timed);
2. makes an opening call through the gateway;
3. runs the cases.

Each case passes only with a finished, non-empty answer that passes its checks (named after the
course dataset's: `exact_numeric`, `contains`). On every call it checks for misroutes from two
sources: the gateway's routing header, and Ollama's list of resident models. It warns on swapping
and on a context window that differs from the config. Learnings are kept in the project's
[journal](../../problem_first_ai/litellm/JOURNAL.md), which the second brain now watches.

## Planned (not built)

- **Planned:** running the three-model lineup (reasoning, text, coding) one after another moves to
  a future project, not this Mac.
- **Planned:** compare the same role across all three tiers: `gpt-6-luna` (frontier), this Mac,
  and Kubernetes-hosted containers on your own NVIDIA GPUs. On the Mac, the vLLM path is
  vllm-metal.
- **Planned:** capture resource utilization even on owned hardware. Scaling up GPUs means a cloud
  bill, with your own hardware as the fallback. So project 06's
  [crossover](../projects/06-sovereign-ai-engine.md#crossover-analysis) is priced against cloud
  GPUs, while utilization is recorded on the owned cluster.
- **Planned:** add a frontier alias for `gpt-6-luna` that reads its key from the environment.
- **Planned:** point Assignment 1's query-understanding part at `local-reasoning`. That's your
  coursework; the gateway side is proven by the course-compatibility case below.

## Where it meets project 06

The note records one conflict with the project 06 page. That page places 06 on the 02–05
Kubernetes stack, with 2–4B models at bf16 on vLLM in phase 2. The note says the Mac is the dev
loop for phases 0–2, and tonight's lineup is a general local set (7–14B, 4-bit). 06's 2–4B
candidates get their own aliases later. The `Conflict` callout on the
[project 06 page](../projects/06-sovereign-ai-engine.md) tracks it until you resolve it.

## Sources

- [Local model gateway — design decisions (2026-10-20)](../../raw/inbox/2026-10-20-local-model-gateway-decisions.md): everything on this page.
- [Local model gateway baseline (2026-10-21)](../../raw/story-updates/2026-10-21-local-model-gateway-baseline.md): every measured figure on this page.
- [`problem_first_ai/litellm/JOURNAL.md`](../../problem_first_ai/litellm/JOURNAL.md): what the build taught, under the course journal's section names.
- [`problem_first_ai/litellm/GLOSSARY.md`](../../problem_first_ai/litellm/GLOSSARY.md): term definitions.
- [`problem_first_ai/litellm/docs/adr/`](../../problem_first_ai/litellm/docs/adr/): ADR 0001 (the Mac is the dev loop) and ADR 0002 (an alias promises a role).
