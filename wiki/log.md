# Log

Append-only. Newest at the bottom. Format: `## [YYYY-MM-DD] action | Title`.
Recent activity: `grep "^## \[" wiki/log.md | tail -5`.

## [2026-10-18] setup | Second brain scaffolding
- Layers: raw/ (sources), wiki/ (compiled), story-bank/ (narratives), tools/brain.py (drift + lint), .claude/ (skills + SessionStart hook).
- Schema: wiki/WIKI_SCHEMA.md; agent operating manual: CLAUDE.md.

## [2026-10-18] ingest | AI infra project roadmap
- Source: raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md
- Created: overview, projects 01–05, concepts kv-cache, continuous-batching, gpu-scheduling, cold-starts, parameter-efficient-finetuning, langgraph-state-graphs.
- Note: source gave titles only for 01–05; designs are marked Proposed.

## [2026-10-18] ingest | Sovereign AI Engine blueprint (Aish)
- Source: raw/roadmaps/2026-10-18-sovereign-ai-engine-blueprint.md
- Created: projects/06-sovereign-ai-engine, concepts quantization and llm-evaluation (both needed by the blueprint's optimizations and metrics), labs/sovereign-ai/crossover.py.

## [2026-10-18] ingest | LangGraph two-call extension plan
- Source: learning-track section of the roadmap; no notebook found in the repo or Google Drive — plan assumes the standard quickstart baseline.
- Created: notebooks/langgraph-two-call-extension, labs/langgraph-two-call/ (module, 9 offline tests, walkthrough notebook). Verified on langgraph 1.2.

## [2026-10-18] heal | Story bank seeded
- Six planned stories in story-bank/stories/, one per project; all Results TBD pending raw/story-updates evidence.

## [2026-10-18] refactor | Track sources in place; notebook-aware hashing; credential lint
- tools/brain.py, .brain/watch.txt, tests/test_brain.py, WIKI_SCHEMA.md, CLAUDE.md

## [2026-10-18] ingest | LangGraph learning notebook (Problem-First AI course)
- source: problem_first_ai/LangChain_LangGraph_Demo.ipynb (tracked in place)
- created: notebooks/langchain-langgraph-demo, concepts/llm-tracing, labs/langgraph-two-call/fortune_extension.ipynb (+ test_notebook.py)
- rewrote: notebooks/langgraph-two-call-extension around the real cells; added gotchas to concepts/langgraph-state-graphs
- verified: companion notebook executed offline (28 cells, all checks pass); planned multi-agent prose review stopped at the session limit

## [2026-10-18] lint | Proofread of the notebook pages (completes the review cut off by the session limit)
- fixed: RetryPolicy backoff timing (extension plan, state-graph gotchas, companion), OpenRouter retry wording, cell-3 status + history-rewrite limits (notebook review)
- all other claims checked against the verified findings; no further changes

## [2026-10-18] ingest | Notebook cell 3 fix + sandbox history rewrite
- source: problem_first_ai/LangChain_LangGraph_Demo.ipynb (cell 3 prints commented out, output removed)
- verified: 0 key-shaped strings reachable from sandbox / PR #1 head (b317927); old SHAs still served by GitHub until purged
- updated: notebooks/langchain-langgraph-demo status

## [2026-10-20] heal | Notebook moved to preread/, course folders ignored
- cause: problem_first_ai/LangChain_LangGraph_Demo.ipynb and requirements.txt moved, byte-identical, into problem_first_ai/preread/ (10 lint errors)
- repointed sources: and links: overview, concepts/langgraph-state-graphs, concepts/llm-tracing, notebooks/langchain-langgraph-demo, notebooks/langgraph-two-call-extension
- notebooks/langchain-langgraph-demo: location note and venv setup now use preread/requirements.txt (no longer committed)
- .gitignore: problem_first_ai/preread/ and problem_first_ai/Assignment 1/ (course material, never published); .brain/watch.txt: + problem_first_ai/preread/*.ipynb
- manifest: new path recorded, REMOVED entry pruned; cell sources match commit 46c74cf (cell-3 fix, already in the review's status note)

## [2026-10-21] ingest | Local model gateway decisions
- source: raw/inbox/2026-10-20-local-model-gateway-decisions.md (copied from problem_first_ai/litellm/docs/2026-10-20-design-decisions.md)
- created: synthesis/2026-10-20-local-model-gateway-plan (tiers, alias rules, first slice, Planned items; links litellm GLOSSARY.md and docs/adr/)
- projects/06-sovereign-ai-engine: Conflict (2026-10-20) callout on the 02–05 stack and bf16 2–4B phase 2 vs the Mac dev loop; Planned note on pricing against cloud GPUs with utilization recorded on owned hardware
- overview: local model gateway track feeding 06 (local, cluster, frontier); index: synthesis row, overview and 06 rows
- story-bank: sovereign-ai-engine synced (Action planned bullets, open thread for the conflict); Result unchanged

## [2026-10-21] ingest | Local model gateway baseline and journal
- touched: synthesis/2026-10-20-local-model-gateway-plan, concepts/cold-starts, concepts/llm-evaluation, overview, index; story-bank/stories/local-model-gateway (new), story-bank/index

## [2026-10-21] ingest | OpenRouter alias first runs and journal (2026-10-21 afternoon)
- touched: synthesis/2026-10-20-local-model-gateway-plan (fourth tier with Conflict callout, OpenRouter first runs, key and alias settings), concepts/cold-starts (loads after Ollama's idle unload), concepts/llm-evaluation (settings a model can't take, failures hiding failures), overview (four tiers), projects/06-sovereign-ai-engine (frontier timings need a direct API), index; story-bank/stories/local-model-gateway (evidence, action, result, open threads), story-bank/index
