---
title: Notebook Review — LangChain & LangGraph Demo (Problem-First AI)
type: notebook
status: active
tags: [langgraph, langchain, notebook, openrouter, arize, security, environment]
sources: [problem_first_ai/LangChain_LangGraph_Demo.ipynb]
related: [notebooks/langgraph-two-call-extension.md, concepts/langgraph-state-graphs.md, concepts/llm-tracing.md]
updated: 2026-10-18
---

# Notebook Review: LangChain & LangGraph Demo

**Source:** [`problem_first_ai/LangChain_LangGraph_Demo.ipynb`](../../problem_first_ai/LangChain_LangGraph_Demo.ipynb).
This is your Problem-First AI course notebook: 53 cells (27 code, 26 markdown), pushed to `sandbox` on
2026-10-18. It is tracked in place through `.brain/watch.txt`, next to its `.venv`.

**How it was reviewed.** Four independent analyses (graph robustness, environment and tracing, gaps
against the plan, security). Each one ran your actual cells in a venv with the model faked. A separate
verifier then tried to refute every finding. Of 31 findings, none was refuted; 18 were corrected in
detail, and this page uses the corrected versions. Versions checked: langgraph 1.2.16, langchain-core
1.6.12, langchain-openrouter 0.2.9, openinference-instrumentation-langchain 0.1.79.

What to build next: [extension plan](langgraph-two-call-extension.md).

## What the notebook covers

| Cells | Topic | What it shows |
|---|---|---|
| 1–10 | LangChain basics | `.env` loading; `init_chat_model("openai/gpt-5-mini", model_provider="openrouter", max_tokens=4000, reasoning={"effort": "minimal"})`; `SystemMessage`/`HumanMessage`; `ChatPromptTemplate`; `.text` |
| 12–26 | Number graph | `TypedDict` state; nodes returning only the keys they change; `START`/`END` edges; `compile()`; `draw_mermaid_png()`; `stream_mode="values"`; `ainvoke` |
| 27–28, 51–52 | Arize tracing | `arize.otel.register` + OpenInference `LangChainInstrumentor` ([LLM tracing](../concepts/llm-tracing.md)) |
| 29–36 | Fortune → joke | Two model calls in sequence; node 2 reads node 1's output from state |
| 37–50 | Sentiment | Classify → respond: a conditional edge with a path map, run sync and async |

**Two canonical two-call patterns are already done.** Cells 38–50 are *classify → respond*. Cells 30–36 are a
sequential two-call, which has the shape of *generate → critique*: only node 2's job changes. The
[extension plan](langgraph-two-call-extension.md) builds on exactly these objects.

## Fix first, in this order

### 1. API key prefixes are in a public repo (cell 3): medium

Cell 3 prints the first 20 characters of `OPENROUTER_API_KEY`, `ARIZE_API_KEY` and `ARIZE_SPACE_ID`. The
saved output is in commit `b5db05f`, on the public `sandbox` branch and in PR #1. How much is exposed:
the OpenRouter value is the public `sk-or-v1-` prefix plus 11 of its 64 secret hex characters. The Arize
value is a 3-character prefix plus 17 characters of a UUID-shaped body. Neither is usable on its own, but
both are now public, so the risk is low but real.

Do these steps **in this order**. If you rotate first and then re-run the old cell 3, the *new* key's
prefix gets written into the notebook.

1. **Replace cell 3** so it reports only whether each value is set, and its length:
   ```python
   import os
   from dotenv import load_dotenv

   load_dotenv()

   REQUIRED = ("OPENROUTER_API_KEY", "ARIZE_API_KEY", "ARIZE_SPACE_ID")
   for name in REQUIRED:
       value = os.environ.get(name, "")
       print(f"{name}: {'set' if value else 'MISSING'} ({len(value)} chars)")
   missing = [n for n in REQUIRED if not os.environ.get(n)]
   if missing:
       raise RuntimeError(f"Add these to .env and restart the kernel: {', '.join(missing)}")
   ```
2. **Rotate the OpenRouter and Arize API keys.** Create new ones, put them in `.env`, restart the kernel,
   then revoke the old ones. The space ID is an identifier and doesn't need rotating.
3. **Strip saved outputs.** To keep only the three graph diagrams:
   `nbstripout --keep-output-type display_data -- problem_first_ai/LangChain_LangGraph_Demo.ipynb`.
   The `--` matters: without it nbstripout reads the filename as an output type and waits silently on
   stdin. To drop all outputs instead:
   `jupyter nbconvert --clear-output --inplace problem_first_ai/LangChain_LangGraph_Demo.ipynb`.
4. **Stop it happening again.** From the repo root, with the venv active: `pip install nbstripout`, then
   `nbstripout --install --attributes .gitattributes`, then `git add --renormalize .`. Without the renormalize,
   outputs already committed stay in HEAD. The filter lives in `.git/config`, so run `--install` once in
   every clone.
5. **Commit on top and squash-merge PR #1.** The squash means `main` never contains the outputs.
   **Don't rewrite history.** The commit is already in a public PR and reachable by SHA, and rotating
   the keys makes the leaked prefixes worthless anyway.

`python3 tools/brain.py lint` flags this pattern now: both the leaked output and the
`os.environ[...][:N]` code that caused it. Values are never printed.

### 2. The notebook ran on your global Python, not the `.venv`: medium

Cell 2 printed `/usr/local/bin/python3`, and warnings in cells 36/46/48/50 load packages from
`/Library/Frameworks/Python.framework/Versions/3.14/...`. That is python.org's global 3.14.3. Cell 0 asks
for the "Python (problem_first_ai)" kernel, but the saved kernelspec is the default "Python 3". Fix:

```bash
cd problem_first_ai
python3 -m venv .venv                 # only if it doesn't exist yet
source .venv/bin/activate
pip install -r requirements.txt       # verified file, committed next to the notebook
python -m ipykernel install --user --name problem_first_ai --display-name "Python (problem_first_ai)"
```

Then pick that kernel (Jupyter: *Kernel → Change Kernel*; VS Code: *Select Kernel*) and restart. Make
cell 2 a check: `import sys; print(sys.executable, sys.prefix != sys.base_prefix)` should print a `.venv`
path and `True`. Wheels exist for CPython 3.14 on Apple silicon and on Intel macOS 11 or later.

### 3. The sentiment router crashes on anything but an exact label: high

`analyze_sentiment` (cell 40) strips whitespace and lowercases, and does nothing else. Replies such as
`"Happy."`, `"**happy**"`, `"neutral"`, `"positive"` or `""` reach cell 42's path map and raise a bare
`KeyError` from inside LangGraph. The saved outputs happen to be clean; cell 38's prompt is the only guard.
The fix is [Step 2 of the plan](langgraph-two-call-extension.md#step-2--harden-the-router).

## Smaller things

- **The `.text()` deprecation warning (cells 36, 46, 48, 50) isn't caused by your code.** `.text` returns a
  callable `str` subclass. Your nodes store it in state, and OpenInference's span masking *calls* any
  callable value, which fires langchain-core's deprecation warning. Upgrading doesn't fix it; the latest
  OpenInference releases still do this. Fix: return `str(model.invoke(prompt).text)` from the nodes in cells
  30 and 40, or filter it *after* langchain-core is imported:
  `warnings.filterwarnings("ignore", message=r"Calling \.text\(\) as a method")`.
- **Cell 50 isn't concurrent.** Two `await`s in a row run one after the other. See
  [Step 6](langgraph-two-call-extension.md#step-6--make-cell-50-actually-concurrent).
- **Re-running cell 28 breaks flushing.** The instrumentor is a singleton, so a second
  `register()`/`instrument()` creates a provider that receives no spans, and cell 52 would flush the wrong
  one. In the saved session cell 28 ran once (no "Overriding of current TracerProvider" in its output).
  Guard the cell with `if "tracer_provider" not in globals():`.
- **Cell 52 never ran** (its `execution_count` is empty). Run it before checking Arize. `force_flush()`
  returning `True` means a flush was *attempted*, not that spans arrived; failures appear only as
  "Failed to export traces" lines on stderr.
- **Cells 5, 9 and 10 run before cell 28, so they aren't traced.** That's expected.
- **Spell the reasoning effort exactly, in lowercase.** `reasoning={"effort": "minimal"}` is the correct,
  first-class ChatOpenRouter parameter. A typo or capital letter (`"Minimal"`) is silently dropped on the
  client, and the model runs at its default effort, using more tokens than cell 5 intends.
- **Retries.** The OpenRouter SDK already retries 5xx and connection errors (2 retries). It doesn't
  retry 429s or dropped connections. A LangGraph `RetryPolicy()` on a node catches those, but would also
  retry a 401 (bad key) or 402 (out of credits) three times.
- **Cell 10** prints the whole `AIMessage`: a 1.9k-character encrypted reasoning blob plus provider IDs.
  It's harmless but noisy. Print `.text` or `usage_metadata` instead.
- **`draw_mermaid_png()`** (cells 21/34/44) sends the graph structure to the public mermaid.ink API, so it
  needs the network. Offline, `get_graph().draw_mermaid()` prints the same diagram as text.
- **On Python 3.14**, importing langchain prints a one-time "Core Pydantic V1 functionality isn't
  compatible with Python 3.14" `UserWarning`. It's harmless.

## Sources

- [`problem_first_ai/LangChain_LangGraph_Demo.ipynb`](../../problem_first_ai/LangChain_LangGraph_Demo.ipynb)
  (commit `b5db05f`): cell sources and saved outputs. Credential values were never read into this page.
- The fixes are encoded as runnable checks in
  [`labs/langgraph-two-call/fortune_extension.ipynb`](../../labs/langgraph-two-call/fortune_extension.ipynb).
