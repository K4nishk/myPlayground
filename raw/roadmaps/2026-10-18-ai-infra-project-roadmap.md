# AI Infrastructure Project Roadmap (as provided 2026-10-18)

Source: transcribed from the session brief that bootstrapped this second brain.
This file records what was *stated*; design detail on the wiki pages that goes
beyond it is marked there as proposed.

## Foundational infrastructure sequence

1. Dockerfile Generator
2. Kubernetes vLLM Serving
3. DevOps / AIOps Platform
4. KServe GPU Autoscaling
5. KEDA Scale-to-Zero
6. Sovereign AI Engine (see `2026-10-18-sovereign-ai-engine-blueprint.md`)

## Cross-cutting concepts called out

- KV cache
- GPU scheduling
- Cold starts
- Continuous batching
- Parameter-efficient fine-tuning
- LangGraph state graphs

## Learning track (parallel)

Learning the LangGraph SDK in a Python notebook: setting up basic agentic
state graphs. Next goal: a robust two-call workflow with explicit State,
Nodes, and Edges, using one of these canonical patterns:

- Explain, then summarize — Node 1 explains a complex concept; Node 2 reads
  that output from state and summarizes it for a five-year-old.
- Generate, then critique — Node 1 generates an initial answer; Node 2
  evaluates gaps, failure modes, or weaknesses in that answer.
- Question, then answer — Node 1 generates a rigorous domain question; Node 2
  provides the structured answer.
- Classify, then respond — Node 1 classifies input sentiment/topic/urgency;
  Node 2 tailors the response based on that classification.

Deliverable: graph compilation code, state definition schema, and execution
trace handling.

## Intent for this repo

A second brain: come in to churn ideas, ask for input, update the wiki. Drop
raw content; the brain absorbs updates and answers from the new data. Maintain
a self-healing `story-bank` used to refine project updates.
