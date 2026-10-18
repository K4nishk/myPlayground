# raw/notebooks/

Export your learning notebooks here (`File → Download → .ipynb`, or
`jupyter nbconvert --to script`). On `/ingest` the agent diffs your notebook
against the extension plan in `wiki/notebooks/` and re-targets the next steps
to where you actually are.

A notebook that has to stay next to its own `.venv` doesn't need to move
here: add its glob to `.brain/watch.txt` and it is tracked in place.

Status 2026-10-18: `problem_first_ai/LangChain_LangGraph_Demo.ipynb` is
tracked in place this way. Its review is `wiki/notebooks/langchain-langgraph-demo.md`
and the plan built on it is `wiki/notebooks/langgraph-two-call-extension.md`.
