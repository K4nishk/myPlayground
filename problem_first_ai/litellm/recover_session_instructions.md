# Resume the gateway work

## Start Claude at the repo root

The sandbox settings (local ports, PyPI, `UV_CACHE_DIR`, write limits) live in the repo root's
`.claude/settings.local.json`, and Claude Code only reads the settings in the folder a session
starts in. Start every session for this work at the root:

```bash
cd ~/Documents/Github/myPlayground && claude                 # new session
cd ~/Documents/Github/myPlayground && claude --continue      # resume the latest one
```

Optional shortcut (R2a). Add it to `~/.zshrc`, then `gw` (or `gw --continue`) starts Claude in the
right place:

```bash
gw() { cd ~/Documents/Github/myPlayground && claude "$@"; }
```

## One-time setup still open

1. **Turn on the pre-commit hook** (R1). It runs `tools/check.sh --staged` before every commit:

   ```bash
   git -C ~/Documents/Github/myPlayground config core.hooksPath .githooks
   ```

2. **CI** runs `tools/check.sh` on GitHub at your next push. Claude doesn't push unless you ask.

## Run the gateway and validate it

Quit memory-heavy apps first: the model needs about 8.2 GiB.

1. **Window A:** Ollama, unless `curl -s localhost:11434/api/version` already answers:

   ```bash
   OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_CONTEXT_LENGTH=4096 ollama serve
   ```

2. **Window B:** the gateway:

   ```bash
   ~/Documents/Github/myPlayground/problem_first_ai/litellm/run_proxy.sh
   ```

3. **In Claude:** "validate the local gateway". Expect 4/4 cases passed and no warnings.
4. Press Ctrl-C in windows B and A when you're done.

## What's waiting on you

See section 9 of `OVERNIGHT-NOTES.md`:

- **N6:** the frontier alias needs `OPENAI_API_KEY` in the gateway's environment, and your OK to
  spend on calls.
- **N7:** vllm-metal is best started in its own session with `/grill-with-docs`.
- **N5:** optionally, point your Assignment 1 Part 1 at the gateway (the snippet is in the notes).
