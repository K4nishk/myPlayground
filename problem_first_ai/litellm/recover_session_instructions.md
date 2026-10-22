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

## Your pending steps

Done on 2026-10-21: the pre-commit hook, the `.claude/settings.json` commit, and the push.

1. **Run the frontier comparison (N6).** `frontier-reasoning` → `openrouter/openai/gpt-6-luna`
   is in the config, and every case now runs on both aliases. `run_proxy.sh` takes
   `OPENROUTER_API_KEY`, and nothing else, from `problem_first_ai/.env`.
   1. Recommended: give that key a credit limit at
      [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys). Anything on this Mac
      that knows the gateway's master key can spend through the alias.
   2. Restart the gateway (window B below) so it loads the new config and the key.
   3. Ask Claude to validate the gateway: 8 cases, each prompt on both aliases.
2. **Curate the draft story** `story-bank/stories/local-model-gateway.md`. Check that the one-liner
   and the résumé bullet sound like you. The interview answer stays TBD until the frontier
   comparison exists.
3. **vllm-metal (N7).** Start it in its own session at the repo root with `/grill-with-docs`.
4. **Optional:** add the `gw` shortcut above, and point your Assignment 1 Part 1 at the gateway
   (N5; the snippet is in section 9 of `OVERNIGHT-NOTES.md`).

## Run the gateway and validate it

Quit memory-heavy apps first: the model needs about 8.2 GiB.

1. **Window A:** Ollama, unless `curl -s localhost:11434/api/version` already answers:

   ```bash
   OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_CONTEXT_LENGTH=4096 ollama serve
   ```

2. **Window B:** the gateway. It reads the OpenRouter key from `problem_first_ai/.env` itself,
   and warns at startup if it can't find one:

   ```bash
   ~/Documents/Github/myPlayground/problem_first_ai/litellm/run_proxy.sh
   ```

3. **In Claude:** "validate the gateway". Expect every case to pass and no warnings.
4. Press Ctrl-C in windows B and A when you're done.
