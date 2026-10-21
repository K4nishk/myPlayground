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

In order. Steps 1–3 take a few minutes; the rest can wait until you want them.

1. **Turn on the pre-commit hook** (R1). It runs `tools/check.sh --staged` before every commit:

   ```bash
   git -C ~/Documents/Github/myPlayground config core.hooksPath .githooks
   git -C ~/Documents/Github/myPlayground config --get core.hooksPath    # prints .githooks
   ```

2. **Decide on your `.claude/settings.json` change.** It's uncommitted, from an earlier session,
   and adds a `Bash(git merge:*)` permission. Commit it or discard it; Claude can't write that file.
3. **Push `sandbox` when you're ready.** The repo is public, so skim what's going out first. CI
   then runs `tools/check.sh` on GitHub:

   ```bash
   git -C ~/Documents/Github/myPlayground log --stat origin/sandbox..sandbox
   git -C ~/Documents/Github/myPlayground push origin sandbox
   ```

4. **Set up the frontier alias's key (N6).** Frontier calls go through OpenRouter and read
   `OPENROUTER_API_KEY`.
   1. At [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys), create a key for this
      gateway only, and give it a credit limit. The limit is what guards your spending: anything on
      this Mac that knows the gateway's master key can call the frontier alias.
   2. Store the key in the macOS Keychain, so it never lands in a file or your shell history.
      With `-w` last, `security` prompts you for the key:

      ```bash
      security add-generic-password -a "$USER" -s openrouter-gateway -w
      ```

   3. Optional: check the key and its remaining limit:

      ```bash
      curl -s https://openrouter.ai/api/v1/key \
        -H "Authorization: Bearer $(security find-generic-password -a "$USER" -s openrouter-gateway -w)"
      ```

   4. Start the gateway with the key in its environment (window B below).
   5. Tell Claude "the OpenRouter key is in place". Claude adds `frontier-reasoning` →
      `openrouter/openai/gpt-6-luna` with the same cases as `local-reasoning`, then validates
      both aliases.
5. **Curate the draft story** `story-bank/stories/local-model-gateway.md`. Check that the one-liner
   and the résumé bullet sound like you. The interview answer stays TBD until the frontier
   comparison exists.
6. **vllm-metal (N7).** Start it in its own session at the repo root with `/grill-with-docs`.
7. **Optional:** add the `gw` shortcut above, and point your Assignment 1 Part 1 at the gateway
   (N5; the snippet is in section 9 of `OVERNIGHT-NOTES.md`).

## Run the gateway and validate it

Quit memory-heavy apps first: the model needs about 8.2 GiB.

1. **Window A:** Ollama, unless `curl -s localhost:11434/api/version` already answers:

   ```bash
   OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_CONTEXT_LENGTH=4096 ollama serve
   ```

2. **Window B:** the gateway, with the OpenRouter key from step 4 in its environment:

   ```bash
   OPENROUTER_API_KEY="$(security find-generic-password -a "$USER" -s openrouter-gateway -w)" \
     ~/Documents/Github/myPlayground/problem_first_ai/litellm/run_proxy.sh
   ```

   Until the frontier alias exists, `run_proxy.sh` on its own is enough.
3. **In Claude:** "validate the local gateway". Expect every case to pass and no warnings.
4. Press Ctrl-C in windows B and A when you're done.
