---
title: LangGraph State Graphs
type: concept
status: draft
tags: [langgraph, agents, orchestration, python]
sources: [raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md, problem_first_ai/preread/LangChain_LangGraph_Demo.ipynb]
related: [notebooks/langgraph-two-call-extension.md, notebooks/langchain-langgraph-demo.md, concepts/llm-tracing.md, projects/01-dockerfile-generator.md, projects/03-devops-aiops-platform.md]
updated: 2026-10-18
---

# LangGraph State Graphs

**One line:** an agent workflow as an explicit graph — a typed **State**
object, **nodes** that read it and return partial updates, and **edges** that
decide what runs next — compiled into a runtime with checkpointing and
streaming. Named as a core concept in the
[roadmap](../../raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md); the
hands-on track is your [course notebook](../notebooks/langchain-langgraph-demo.md) and the
[two-call extension plan](../notebooks/langgraph-two-call-extension.md). Notes reflect LangGraph 1.x.

## The pieces

| Piece | What it is | Gotcha |
|---|---|---|
| **State** | `TypedDict` (or dataclass / Pydantic) shared by all nodes | Every key is a *channel*; design it like an API |
| **Reducer** | How updates to a key merge: default overwrite; `Annotated[list, operator.add]` appends; `add_messages` merges chat messages by id | Without a reducer, two nodes writing one key in the same step is an error |
| **Node** | `def node(state) -> dict` returning only the keys it changes | Don't mutate `state` in place — return the update |
| **Edge** | `add_edge(a, b)`; `START` and `END` are the entry/exit sentinels | Two outgoing edges from one node = both run in parallel next step |
| **Conditional edge** | `add_conditional_edges(src, router, {label: node})` | The router returns a label; keep it pure and cheap |
| **Compile** | `builder.compile(checkpointer=…)` → runnable graph | Structure errors (unknown node, unreachable) surface here |

## Runtime model

Execution proceeds in **super-steps**: all nodes triggered in a step run,
their updates are merged through reducers, then the next set is chosen. A
**checkpointer** (`InMemorySaver` for notebooks; SQLite/Postgres savers for
real use) snapshots state after every step, keyed by `thread_id` in
`config={"configurable": {"thread_id": …}}`. That gives you:

- `graph.get_state(config)` — latest snapshot (`.values`, `.next`).
- `graph.get_state_history(config)` — every step, newest first: replay,
  debugging, time travel.
- **Human-in-the-loop:** `interrupt(...)` inside a node pauses the run;
  resume with `graph.invoke(Command(resume=value), config)`.

## Streaming modes (`graph.stream(..., stream_mode=...)`)

| Mode | Yields | Use |
|---|---|---|
| `"values"` | full state after each step | watching state evolve |
| `"updates"` | `{node: update}` per node | execution traces (the two-call plan uses this) |
| `"messages"` | LLM tokens + metadata | streaming UIs |
| `"custom"` | whatever nodes emit via a stream writer | progress events |
| `"debug"` | everything | deep debugging |

Pass a list (`["updates", "values"]`) to get `(mode, chunk)` tuples.

## Patterns worth knowing

- **Input/output schemas:** `StateGraph(State, input_schema=In, output_schema=Out)`
  keeps internal scratch keys out of the public contract.
- **Runtime context:** `context_schema=` injects per-run dependencies (model
  name, user id) without putting them in state.
- **`Send`** for map-reduce fan-out; **subgraphs** for reusable components.
- **Retry policies** on flaky nodes (`add_node(..., retry_policy=RetryPolicy(...))`).

## Gotchas (verified 2026-10-18, langgraph 1.2.16)

Each of these was reproduced by running your notebook's cells with a fake model:

| Gotcha | What happens | Do instead |
|---|---|---|
| Router returns a label missing from the path map | Bare `KeyError: '<label>'` raised inside LangGraph's branch code; the only context is "During task with name …" | Validate in the node and raise a clear error ([Step 2](../notebooks/langgraph-two-call-extension.md#step-2--harden-the-router)) |
| `Literal[...]` on a `TypedDict` field | Documentation and JSON schema only; values aren't checked at runtime | Validate in nodes, or use a Pydantic state (raises `ValidationError` on read) |
| `Literal[...]` on a router's return type | Ignored at runtime when a path map is given; *without* one it defines the targets, so its values must be node names or `"__end__"` | Use node names when relying on inference (Step 5) |
| `RetryPolicy()` defaults | `retry_on` returns `False` for `ValueError`, `TypeError`, `LookupError` (incl. `KeyError`); backoff starts at 0.5 s and doubles, plus up to 1 s of random jitter | Pass `retry_on=`; a list of policies applies the first that matches |
| Default `recursion_limit` | 10,007 steps in 1.2.16, so it's no safety net for a loop | Pass `recursion_limit` on every invoke of a looping graph |
| Error *after* a node wrote state, with a checkpointer | Thread looks finished (`next == ()`); resuming does nothing; downstream keys are missing | Fail inside the node before returning an update |
| `await a` then `await b` | Runs sequentially | `asyncio.gather(...)` or `graph.abatch(...)`, with `return_exceptions=True` |
| Sync `def` nodes under `ainvoke`/`abatch` | Run in a thread pool (`min(32, cpu_count + 4)` workers) | Fine for small runs; `async def` nodes lift the cap but break plain `invoke()` |
| Batch runs sharing one `thread_id` | Their checkpoints interleave in one history | One `thread_id` per input |
| Re-defining a node function | The compiled graph keeps the old function | Re-run the builder and `compile()` |

## Used by

[Your course notebook](../notebooks/langchain-langgraph-demo.md) ·
[Two-call extension](../notebooks/langgraph-two-call-extension.md) ·
[01 Dockerfile generator](../projects/01-dockerfile-generator.md) (generate → verify → repair) ·
[03 AIOps triage agent](../projects/03-devops-aiops-platform.md) (classify → respond, interrupts)

## Sources

- [AI infra project roadmap](../../raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md) — named as a core concept; LangGraph learning track.
- Background: LangGraph documentation (langchain-ai.github.io/langgraph); API checked against `langgraph` 1.2.
