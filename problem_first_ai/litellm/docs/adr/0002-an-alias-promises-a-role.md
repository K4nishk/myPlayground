---
status: accepted
---

# An alias promises a role, not a model

An alias such as `local-reasoning` names a role at a tier and may be re-pointed to another backend model, for example from Ollama to vllm-metal or to a newer model. So every run records the backend model behind each alias, baselines are keyed by alias plus backend model, and re-pointing an alias starts a new baseline. Experiments use candidates (aliases pinned to one backend model and never re-pointed), so a role alias never changes meaning mid-experiment.
