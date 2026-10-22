# 2026-10-20 — Local model gateway — design decisions

Decided by Kanishk in a design session in `problem_first_ai/litellm/`; written up by Claude.
Terms are defined in [`GLOSSARY.md`](../GLOSSARY.md); the two hard-to-reverse decisions are in
[`docs/adr/`](adr/).

## Decided

- A LiteLLM gateway is the routing layer between a frontier API and open-weight models, in the
  direction of project 06. Reasons: learning LiteLLM, and running coursework against models other
  than `gpt-6-luna`.
- Three tiers: `local` is this Mac (M3 Pro, 18 GB), `cluster` is Kubernetes on my own NVIDIA
  hardware, `frontier` is a vendor API. Aliases are named `<tier>-<role>` and promise a role, not
  a model ([ADR 0002](adr/0002-an-alias-promises-a-role.md)).
- The Mac is the dev loop; capacity and resource utilization are measured on the cluster
  ([ADR 0001](adr/0001-mac-is-the-dev-loop.md)).
- First slice, built the evening of 2026-10-20: one alias, `local-reasoning` → `deepseek-r1:14b` on
  Ollama 0.40.6, a 4096-token context window, one model resident at a time; the gateway on
  `127.0.0.1:4000` serving both Chat Completions and the Responses API; an end-to-end validator
  skill that every later change must pass.
- `deepseek-r1:14b` cannot call tools (its Ollama prompt template has no tools section), so it can
  serve Assignment 1's query-understanding part but not the tool or ReAct parts.
- LiteLLM is pinned to an exact version (1.103.3, the newest release at least 14 days old) with a
  lockfile, because releases 1.82.7 and 1.82.8 were compromised on PyPI in March 2026. No key value
  is written to any file; only frontier aliases read a key, from the environment.
- Course material is never published: `problem_first_ai/preread/` and
  `problem_first_ai/Assignment 1/` stay out of git.

## Planned (not built)

- Running the three-model lineup (reasoning, text, coding) one after another moves to a future
  project, not this Mac.
- Compare the same role across all three tiers: `gpt-6-luna` (frontier) vs this Mac vs
  Kubernetes-hosted containers on my own NVIDIA GPUs. On the Mac, the vLLM path is vllm-metal.
- Capture resource utilization even on owned hardware: scaling up GPUs means a cloud bill, with my
  own hardware as the fallback. So project 06's crossover is priced against cloud GPUs while
  utilization is recorded on the owned cluster.
- Add a frontier alias for `gpt-6-luna` later, reading its key from the environment. Updated
  2026-10-21: it goes through OpenRouter (`openrouter/openai/gpt-6-luna`) and reads
  `OPENROUTER_API_KEY`, because the OpenRouter account has the budget for these calls. Its
  latencies will include OpenRouter's hop, which matters when comparing it with the local tiers.
- Keep journaling learnings in `problem_first_ai/litellm/JOURNAL.md` as later projects build on
  this one.

## Conflicts with the wiki

- The project 06 page says 06 runs on the Kubernetes stack from projects 02–05, with 2–4B models at
  bf16 on vLLM. Now: the Mac is the dev loop for phases 0–2, and tonight's lineup is a general
  local set (7–14B, 4-bit). 06's 2–4B candidates get their own aliases later.
