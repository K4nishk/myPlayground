---
status: accepted
---

# One local backend holds a model at a time; a candidate runs from its own config

18 GB can't hold two 14B models. A vLLM server also holds its weights from start to stop (vllm-metal v0.30.0 has no sleep mode), whereas an Ollama server can sit idle with nothing loaded. So only one local backend server runs at a time: while vLLM runs, Ollama is stopped, not just unloaded, and the reverse.

A run covers every alias the gateway knows. A candidate on a backend that's usually off therefore doesn't go in `litellm_config.yaml`. Instead it gets its own gateway config, plus a frozen copy of the cases, in its experiment's folder (`experiments/<date>-<name>/`), and `run_proxy.sh` takes that config's path. The daily config names only backends that are expected to be running.

## Considered Options

- **Keep Ollama up with its model unloaded while vLLM runs:** rejected. One stray call to a local Ollama alias would load 8 GB on top of vLLM.
- **Put the candidate in the daily config and give the runner an alias filter:** rejected. Every ordinary run would fail with `backend_unhealthy` while vLLM is off, or a partial run would need its own definition.
