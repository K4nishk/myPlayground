---
title: LLM Tracing (OpenTelemetry · OpenInference · Arize)
type: concept
status: draft
tags: [observability, tracing, opentelemetry, openinference, arize, langgraph]
sources: [problem_first_ai/preread/LangChain_LangGraph_Demo.ipynb]
related: [concepts/langgraph-state-graphs.md, concepts/llm-evaluation.md, notebooks/langgraph-two-call-extension.md, projects/03-devops-aiops-platform.md]
updated: 2026-10-18
---

# LLM Tracing

**One line:** record every model call, with its prompt, reply, tokens and latency, as an OpenTelemetry
span nested under the workflow step that made it, so you can see *why* an agent did what it did, not just
what it returned. Your notebook does this with Arize
([cells 28 and 52](../notebooks/langchain-langgraph-demo.md#what-the-notebook-covers)).

## The stack

| Layer | Role | In your notebook |
|---|---|---|
| OpenTelemetry SDK | Spans, a tracer provider, a batch exporter (OTLP) | created by `arize.otel.register(...)` |
| OpenInference | LLM-specific span conventions plus auto-instrumentation for LangChain/LangGraph | `LangChainInstrumentor().instrument(tracer_provider=...)` |
| Backend | Stores and visualizes traces; runs evals on them | Arize project `langGraph-demo` |

The instrumentor hooks LangChain's callback manager, so every model, prompt and graph run *after* cell 28
is traced, including a `model` created earlier. Calls made before it (your cells 5/9/10) are not.

## What a LangGraph run looks like

One trace per `invoke`: a root span for the graph, a child span per node, and under each node the
`ChatPromptTemplate` and chat-model spans. A fortune → joke run produces **7 spans**: the graph root, two
nodes, and a prompt span plus a model span under each node. The model spans carry the input and output
messages, token counts and latency.

**Sessions:** when you invoke with `config={"configurable": {"thread_id": ...}}`, OpenInference copies the
`thread_id` into every span of that run as `session.id`. Your checkpoint history
([LangGraph state graphs](langgraph-state-graphs.md)) and Arize's Sessions view then share one key.
Without a config, `session.id` is `None`.

## Gotchas (verified 2026-10-18)

- **Flushing.** The batch processor exports every 5 s and on interpreter exit. `force_flush()` returns
  `True` whenever the processor is alive, **even if every export failed**. Delivery failures show up only
  as "Failed to export traces …" log lines on stderr.
- **Re-running the setup cell.** Instrumentors are singletons. A second `register()` + `instrument()` is a
  no-op for the instrumentor, but rebinds your `tracer_provider` variable to a new provider that receives
  no spans, so a later `force_flush()` flushes the wrong one. Guard the cell with
  `if "tracer_provider" not in globals():`.
- **Masking calls callables.** OpenInference's `TraceConfig.mask` calls any callable attribute value.
  langchain-core's `.text` returns a callable `str` subclass, so storing it in graph state fires a
  `.text()` deprecation warning from inside `_spans.py`. Store `str(...)` instead. Upgrading packages
  doesn't change this.
- **Test runs pollute the project.** A fake model run under the instrumentor still produces spans. Run
  offline tests before instrumenting, or point tests at a separate `project_name`.

## Tracing vs the other two views

| Question | Use |
|---|---|
| What exactly did the model see, and how long did it take? | Tracing (spans) |
| What did each node write, live? | `stream_mode="updates"` |
| What was the full state at step *k*, and can I resume from it? | Checkpointer + `get_state_history` |

Step 4 of the [extension plan](../notebooks/langgraph-two-call-extension.md#step-4--execution-trace-handling)
wires all three together.

## Why it matters beyond the notebook

- **[03 AIOps](../projects/03-devops-aiops-platform.md):** the triage agent's own decisions need the same
  audit trail as the systems it diagnoses.
- **[LLM evaluation](llm-evaluation.md):** traces are the raw material for LLM-as-judge evals and for
  latency percentiles per step.

## Sources

- [`problem_first_ai/preread/LangChain_LangGraph_Demo.ipynb`](../../problem_first_ai/preread/LangChain_LangGraph_Demo.ipynb), cells 28, 36, 46–52 (saved outputs).
- Behaviour reproduced 2026-10-18 with openinference-instrumentation-langchain 0.1.79 and the OpenTelemetry SDK, using a fake model.
