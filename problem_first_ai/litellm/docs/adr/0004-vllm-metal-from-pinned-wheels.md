---
status: accepted
---

# vllm-metal is installed from pinned wheels in its own uv project

Neither of vllm-metal's own install paths meets the supply-chain rule (exact pins, releases at least 14 days old, a lockfile). Its `install.sh` installs the newest dev build by default, or the latest release with `--stable`. When piped from curl it fetches its helper script from `main`, and it checks no hashes. The Homebrew formula tracks the newest release and resolves `mlx` and `mlx-lm` without hashes.

So the vLLM backend lives in its own uv project, `backends/vllm-metal/`, pinned as follows:

- **Python 3.12:** the wheels are built for 3.12 only, and the gateway runs 3.13.
- **The vLLM and vllm-metal wheels:** by URL and sha256.
- **`mlx-lm`:** by the git commit the release names.
- **`transformers`:** pinned explicitly, since the release sets no upper bound.
- **Everything else from PyPI:** under `exclude-newer`. uv's `exclude-newer` doesn't cover URL or git sources, so those are checked for age by hand, and each check is recorded next to its pin.

The runner never imports vLLM: it stays in the gateway's environment and talks to vLLM over HTTP.

## Considered Options

- **`install.sh` or `brew install vllm-metal`:** rejected, because each installs whatever is newest and checks no hashes.
- **One uv project for the gateway and vLLM:** rejected. The Python versions differ, and vLLM's pins (torch, transformers, fastapi, openai) would fight LiteLLM's, so every vLLM upgrade would re-lock the gateway.
