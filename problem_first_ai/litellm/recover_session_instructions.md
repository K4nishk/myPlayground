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

## Run the gateway and test it

Follow [user-guide.md](user-guide.md): it starts Ollama and the gateway, calls each alias by hand,
and runs the validator.

## Your pending steps

Done on 2026-10-21: the pre-commit hook, the `.claude/settings.json` commit, the push, and the
OpenRouter alias.

1. **Restart the gateway.** The OpenRouter alias is now `openrouter-reasoning`
   ([ADR 0003](docs/adr/0003-openrouter-is-its-own-tier.md)); until the gateway restarts, the
   validator reports `alias_mismatch`. Then work through `user-guide.md` once. Recommended: give
   the OpenRouter key a credit limit at [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys).
2. **A clean run for a baseline.** Quit memory-heavy apps, then ask Claude to validate the
   gateway. A run with no warnings becomes the first local-vs-OpenRouter baseline: a story update
   in `raw/story-updates/`, then the second brain's ingest.
3. **Curate the draft story** `story-bank/stories/local-model-gateway.md`. Check that the one-liner
   and the résumé bullet sound like you.
4. **vllm-metal (N7).** Start it in its own session at the repo root with `/grill-with-docs` and
   the prompt below.
5. **Push** `sandbox` when you're ready; CI runs `tools/check.sh` on GitHub.
6. **Optional:** add the `gw` shortcut above, and point your Assignment 1 Part 1 at the gateway
   (N5; the snippet is in section 9 of `OVERNIGHT-NOTES.md`).

## The vllm-metal prompt

```text
/grill-with-docs Plan running the local model gateway's Mac tier on vLLM through vllm-metal (item N7), so it can be compared with the Ollama baseline. Plan only: don't install, pull or start anything in this session.

Read first:
- problem_first_ai/litellm/README.md, GLOSSARY.md, docs/adr/ (all three), docs/2026-10-20-design-decisions.md
- problem_first_ai/litellm/OVERNIGHT-NOTES.md (N7 and section 9) and JOURNAL.md
- raw/story-updates/2026-10-21-local-model-gateway-baseline.md — the Ollama numbers to compare against
- problem_first_ai/litellm/validator/scripts/e2e_runner.py — it probes Ollama only; any other backend is "not probed"
- wiki/synthesis/2026-10-20-local-model-gateway-plan.md

Where things stand: M3 Pro, 18 GB, macOS 15.1.1. local-reasoning → deepseek-r1:14b (Q4_K_M) on Ollama 0.40.6, 4096-token context, one model resident at a time, measured at 14.8 tokens/s and 8.23–8.83 GiB, all on the GPU. LiteLLM 1.103.3 is pinned with uv and exclude-newer. openrouter-reasoning goes to gpt-6-luna through OpenRouter; frontier-* is kept for a vendor API called directly.

Rules that still apply:
- Supply chain: exact pins, releases at least 14 days old, a lockfile, nothing unpinned. Ask before any brew install.
- Measured numbers cite a raw/story-updates/ note; plans are labelled Planned or Proposed.
- No course content in tracked files; no key values in any file.
- 18 GB can't hold two 14B models, so decide how vLLM and Ollama share memory.

Grill me on at least:
1. Is vllm-metal maintained enough to build on? Which version and Python, installed how, and in its own uv project or the gateway's?
2. Which model and format: the same deepseek-r1 14B distill in a 4-bit format vLLM on Metal can load, so the comparison with Q4_K_M is fair? What's the 8B fallback?
3. Re-point local-reasoning (a new baseline under ADR 0002), or add a Candidate alias pinned to the vLLM model?
4. LiteLLM's route prefix for it, and whether reasoning_content, the Responses API and reasoning_effort survive the trip.
5. The runner's vLLM backend: health and served-model probes, what counts as a load, how to measure memory without Ollama's /api/ps, and tests at the command-line seam.
6. What to measure and the success criteria, against the baseline note.

Record decisions as ADRs and glossary entries as we go, and finish with a dated decisions doc in problem_first_ai/litellm/docs/.
```
