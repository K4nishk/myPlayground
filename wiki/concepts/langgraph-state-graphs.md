---
title: LangGraph State Graphs
type: concept
status: draft
tags: [langgraph, agents, orchestration, python]
sources: [raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md]
related: [notebooks/langgraph-two-call-extension.md, projects/01-dockerfile-generator.md, projects/03-devops-aiops-platform.md]
updated: 2026-10-18
---

# LangGraph State Graphs

**One line:** an agent workflow as an explicit graph — a typed **State**
object, **nodes** that read it and return partial updates, and **edges** that
decide what runs next — compiled into a runtime with checkpointing and
streaming. Named as a core concept in the
[roadmap](../../raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md); the
hands-on track is the [two-call extension plan](../notebooks/langgraph-two-call-extension.md).
Notes reflect LangGraph 1.x.

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

## Used by

[Two-call extension](../notebooks/langgraph-two-call-extension.md) ·
[01 Dockerfile generator](../projects/01-dockerfile-generator.md) (generate → verify → repair) ·
[03 AIOps triage agent](../projects/03-devops-aiops-platform.md) (classify → respond, interrupts)

## Sources

- [AI infra project roadmap](../../raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md) — named as a core concept; LangGraph learning track.
- Background: LangGraph documentation (langchain-ai.github.io/langgraph); API checked against `langgraph` 1.2.
