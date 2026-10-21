# Overnight notes — 2026-10-20/21

**Status:** built, passing, reviewed twice. Nothing is committed (this session can't write
`.git`). Your morning steps are in `recover_session_instructions.md`; this file is what you
review.

Numbering for your replies: **D** = decisions on the build, **R** = retro proposals (changes to
the setup around Claude), **N** = proposed next steps.

## 1. What passed

- **Live:** 9 of 9 validator runs passed, 3/3 cases each: Chat Completions arithmetic, a Chat
  Completions riddle, and Responses API arithmetic. No swapping in any run.
  - Two deliberate failure runs (a wrong key, a dead port) reported `gateway_rejected_key` and
    `gateway_unreachable`.
- **Offline:** 27 tests pass, confirmed separately by the second Spec reviewer.
- **`setup.sh`:** ran five times, the last on its final version, every time with exit 0 and
  everything reported in place. Two gaps:
  - Only my session output shows these runs; nothing was logged to disk (see R5).
  - Its branches that **install Ollama, start Ollama or pull a model have never run**, because
    all three were always already done.
- **Pins:** LiteLLM 1.103.3, openai 2.54.0, and every package resolved as of 2026-10-06 (663
  hashes in `uv.lock`). The malware file from the compromised releases (`litellm_init.pth`) is
  absent.
- **Server settings:**
  - The context window was confirmed at 4096 in every run, from Ollama's `/api/ps`.
  - `OLLAMA_MAX_LOADED_MODELS=1` can't be read through Ollama's API. You confirmed it visually
    in window A last night.

## 2. Measured results

All in `runs/baseline-story-update.md`, which becomes
`raw/story-updates/2026-10-21-local-model-gateway-baseline.md` in Prompt B. Headline from the
last three runs:

| Case | API | Latency | Output tokens | Tokens/s |
|---|---|---|---|---|
| reasoning-arithmetic | chat | 17.19–17.24 s | 255 | 14.8 |
| reasoning-riddle | chat | 20.78–20.90 s | 309 | 14.8–14.9 |
| reasoning-responses-api | responses | 13.09–13.14 s | 193 | 14.7 |

- **Resident memory:** 8.23 or 8.83 GiB, all on the GPU, context window 4096.
- **Swap:** 0 pages swapped out.
- **Cold calls:** about 2 s after the model sat idle, 6–7 s straight after an unload. The cause
  is open (see N4).

**Caveats the reviewers raised:**

- **The runner changed after the last cited run.** Its comment was edited, with no logic
  change, and the tests passed after. The baseline note shouldn't say "final runner" without
  that caveat; Prompt B can add it when it ingests the note.
- **The "after idling" vs "straight after an unload" split comes from my log of the session,**
  not from the reports. The reports don't record whether the model was loaded before a run (N2).
- **Five figures aren't in any run report:** Q4_K_M / 14.8B, the 45 reasoning characters, the
  0.02 s unload test, the 12.0 GiB of swap and the 4.8 GiB compressed. They're recorded with
  how they were measured in the baseline note itself.

## 3. What was built (under `problem_first_ai/litellm/`)

- **Gateway files:** `setup.sh`, `run_proxy.sh`, `litellm_config.yaml`, `pyproject.toml`,
  `uv.lock`, `.python-version`, `.gitignore`
- **The skill, staged** at `skill-staging/local-model-e2e-validator/` until you move it:
  `SKILL.md`, `cases.yaml`, `scripts/e2e_runner.py`, `tests/test_e2e_runner.py`
- **Docs:** `README.md` (layout and install steps), `JOURNAL.md`, and these notes
- **Local only, git-ignored:** `runs/` (9 run reports plus the baseline draft) and `logs/proxy.log`

## 4. Code review, round 1 (all fixed overnight)

Measured numbers now have sources. The runner follows the lab code's style and the glossary's
names, and Ollama's fields are parsed only inside `OllamaBackend`. The check types and API names
each come from a single lookup table, and config errors are caught only while loading. Every
alias's backend model is recorded even when a run stops early (ADR 0002). `setup.sh` handles
untagged model names and the `ollama/` prefix. `run_proxy.sh` is fixed to `127.0.0.1:4000`.
`drop_params` is removed. The skill's tables and diagnosis commands are complete.

**My own correction:** I had recorded a fast cold call as a runner bug. A direct test disproved
it, and I removed the claim everywhere.

## 5. Code review, round 2 (open, on the final state)

The two reviews are kept separate, as the code-review skill requires.

### Standards
- **Hard: a source that doesn't exist yet.** README and JOURNAL cite
  `raw/story-updates/2026-10-21-local-model-gateway-baseline.md`, which only exists once
  Prompt B copies the draft. Prompt B does that copy before it commits.
- **Hard: an uncited figure.** SKILL.md's "8.99 GB download" comes from Ollama's registry
  manifest but isn't cited (D8).
- **Glossary:**
  - The skill's description says "wrong model"; the glossary term is *misrouted*.
  - The call made before an alias's cases has no glossary term and four names in the code
    (D6).
- **Smells (judgement calls):**
  - `start_alias` times `call_chat` again, though the call already returns its latency.
  - The exception tuple `(URLError, OSError, ValueError)` is repeated, and `URLError` is
    already an `OSError`.
  - Warnings are built inline next to the `failure()` helper.
  - `setup.sh` re-implements the runner's config parsing and Ollama tag logic in shell.
  - `run_proxy.sh` writes `127.0.0.1` / `4000` as literals four times.
  - `(alias, backend)` travels together everywhere.
  - `cold_call_s` and `warm_call_s` are two fields of which only one is ever set.
  - Failure kinds are bare strings.
  - `BACKENDS` is a map holding a single class.
  - Several lines run past the labs' 120-character width.
  - The test docstring says "only the network boundary is replaced", but `vm_stat` is
    replaced too.
- **Clean:** no credential values, the illustrative table is labelled, and the tests use only
  the standard library.

### Spec
- **Missing or partial:**
  1. `setup.sh`'s server-start branch is untested, and the re-runs aren't logged to disk.
  2. The cited raw/ baseline doesn't exist until Prompt B (same as Standards above).
  3. **A run can pass without covering every alias.** The glossary's *Run* covers the cases of
     every alias, but a config alias with no cases still lets the run pass, and a case with no
     check is accepted (D7).
  4. **The opening call isn't checked for a misroute**; only the cases are (N2).
- **Scope creep (minor, justified):** `LITELLM_GATEWAY_URL`, the bundled cost map, the
  port-in-use guard, `telemetry: false`, uv installed via brew, the per-alias GPU figure, the
  `gateway_rejected_key` kind, and support for the plain `ollama/` prefix. SKILL.md also
  hard-codes `127.0.0.1:11434`, which works against "generic for N aliases" (D8).
- **Looks wrong:**
  5. **"Cold call" isn't load time.** It includes the 16-token opening answer, roughly 1 s of
     the 2 s figure (N2, N4).
  6. **The journal's sub-labels copy the template's question titles,** e.g. "Metric-to-system
     mapping", "Most impactful design choices", "Hardest roadblock". That goes past "section
     names only" (D5).
  7. The baseline's "final runner" claim needs the comment-only caveat (section 2).

## 6. Decisions waiting for you

- **D1. Test hook `E2E_RUNNER_VM_STAT`.** It's a third test boundary beyond the two agreed in
  Q33. *Proposed:* keep it, and fix the test docstring to say `vm_stat` is replaced too.
- **D2. Extras beyond the spec.**
  - The gateway-header misroute check (`x-litellm-model-name`)
  - `--keep-resident`
  - The available-memory figure
  - `exclude-newer` for the whole dependency tree
  - `LITELLM_GATEWAY_URL`
  - The port-in-use guard
  - Support for the plain `ollama/` prefix

  *Proposed:* keep them all.
- **D3. TDD note.** The `exact_numeric` final-number logic was written in the first slice, so
  its two tests passed straight away; every other slice went red first. *Proposed:* note it and
  move on.
- **D4. `deepseek-r1:8b`** (5.23 GB) is downloaded but unused. *Proposed:* keep it as the
  backup reasoning model until the vllm-metal work, then decide.
- **D5. Journal sub-labels** (course-content rule). *Proposed:* replace the template's question
  titles with my own wording, keeping only the four section names, before Prompt B commits.
- **D6. A name for the call made before an alias's cases.** *Proposed:* **opening call**.
  - Add it to `GLOSSARY.md`.
  - Rename `START_*`/`start_alias` and the tests to match.
  - Replace `cold_call_s`/`warm_call_s` with `opening_call_s` plus the existing `cold` flag.
- **D7. Run completeness.** *Proposed:* make it a config error for an alias to have no cases
  or a case to have no check, so a passing run always covers every alias.
- **D8. SKILL.md specifics.** *Proposed:*
  - Have the skill read backend addresses from the report rather than hard-coding
    `127.0.0.1:11434`.
  - Cite the 8.99 GB download size in the baseline note (from Ollama's registry manifest).
  - Change "wrong model" to "misrouted".

## 7. Retro proposals (by severity)

All *Proposed*. Each is a change to the setup around Claude, not to the gateway.

- **R1. Add a guardrail (automated checks).** The repo has no CI, no pre-commit hook and no
  active git hooks, so nothing runs the existing tests or `brain.py lint` before a commit or
  push. *Proposed:* one GitHub Actions workflow plus a matching local pre-commit hook. They
  would run:
  - `python3 tools/brain.py lint`
  - `python3 -m unittest discover -s tests`
  - the validator's offline tests, through `uv run --frozen`
  - `bash -n` (and shellcheck, if you want it) on `setup.sh` and `run_proxy.sh`
- **R2. The starting-folder trap (information access).** Resuming from `problem_first_ai/`
  silently dropped the sandbox settings, which cost a full check-and-relaunch cycle and could
  stall an unattended run. *Proposed:*
  - (a) A shell function, e.g. `gw() { cd ~/Documents/Github/myPlayground/problem_first_ai/litellm && claude "$@"; }`,
    so the right folder is the easy path.
  - (b) A row in the skill's diagnosis table: "`Operation not permitted` on 127.0.0.1 means
    this session started outside `litellm/`."
  - (c) Test whether the repo-root `.claude/settings.local.json` applies to sessions started in
    subfolders; if it does, move the sandbox block there.
- **R3. Move the skill's code out of the protected folder (navigation).** Claude can't write
  under `.claude/skills/`. That forced last night's staging-and-`mv` step, broke the doc paths
  until the move, and will block every future runner fix by an agent. *Proposed:*
  - Move `scripts/`, `tests/` and `cases.yaml` to `problem_first_ai/litellm/validator/`.
  - Keep only `SKILL.md` in the skill folder, pointing at them.
  - Then only edits to SKILL.md itself need your approval.
- **R4. A reviewer standard for claims (coding standards).** My unverified "unload loads the
  model" claim went into a code comment, a test, the journal and the baseline before anyone
  tested it, and the first review didn't flag it. This is a judgement call, not a mechanical
  one. *Proposed:* a short `CODING_STANDARDS.md` for the reviewer, starting with: "A statement
  about how a dependency behaves needs a test or a cited observation; otherwise label it a
  hypothesis."
- **R5. Keep evidence on disk (information access).** Reviewers couldn't verify the `setup.sh`
  re-runs or the idle-vs-unload split, because that evidence lived only in this session.
  *Proposed:*
  - `setup.sh` copies its output to `logs/setup.log`.
  - The runner records whether each model was loaded before the run (N2).
- **R6. Writing the second brain and git from a `litellm/` session.** *Proposed, your
  trade-off:*
  - **Either** grant writes to `wiki/`, `.brain/`, `story-bank/` and `.git` only (never `raw/`),
    using `permissions.additionalDirectories` plus a sandbox `allowWrite` entry;
  - **or** keep the Prompt A/B handoff, which worked but costs you a second session each time.
- **R7. `UV_CACHE_DIR` everywhere (tool economy).** Every command needed the prefix, and the
  cache in the temp folder is cleared on restart. *Proposed:*
  - Set `"env": {"UV_CACHE_DIR": "<litellm>/.uv-cache"}` in `litellm/.claude/settings.local.json`.
  - Git-ignore `.uv-cache/`.
  - Remove the prefix instruction from SKILL.md.
- **R8 (no change).** One `cd` into the venv moved this session's working directory and shrank
  where I could write. The lesson is to use absolute paths, which Claude Code's own guidance
  already says.

## 8. Proposed next steps

- **N1. This morning:** answer D1–D8, choose R1–R7, move the skill (after R3 if accepted), then
  run Prompt B to ingest and commit.
- **N2. Small runner follow-ups,** if D6/D7 are accepted:
  - Check the opening call for a misroute.
  - Record whether each model was loaded before the run.
  - Time the load on its own, using Ollama's `load_duration` from a zero-token load, separately
    from the opening call.
  - Remove the duplicated exception tuples and inline warnings.
  - Make the failure kinds constants.
  - Keep lines to 120 characters.
- **N3. A settings-drift warning.** Warn when Ollama's reported context window differs from the
  config's `num_ctx`, so every run re-verifies `OLLAMA_CONTEXT_LENGTH`.
  `OLLAMA_MAX_LOADED_MODELS` can't be read through the API, so it stays a startup check.
- **N4. Settle the cold-call question** (about 2 s after idling vs 6–7 s straight after an
  unload) with N2's separate load timings over a few runs. Record the result in a story update.
- **N5. Course compatibility.** Point Perplexia's Part 1 (query classification) at
  `local-reasoning` through `base_url`, and add a course-compatibility case to `cases.yaml`
  (Responses API plus `reasoning_effort`). Parts 2–3 need a tools-capable alias.
- **N6. A frontier alias.** Add `frontier-reasoning` → `gpt-6-luna` through OpenRouter, reading
  `OPENROUTER_API_KEY` from the environment (it was `OPENAI_API_KEY` until 2026-10-21), and run
  the same cases. That's the first frontier-vs-local comparison for project 06, phase 1.
- **N7. vllm-metal on this Mac.** Re-point `local-reasoning` (a new baseline under ADR 0002),
  and add a vLLM backend probe (`/health`, served models) to the runner.
- **N8. The three-model lineup and the cluster tier** go in a future project on other
  hardware, starting with `/grill-with-docs`.
- **N9. Keep `JOURNAL.md` going** for each project; after Prompt B the second brain absorbs it
  automatically.

## 9. Morning follow-up, 2026-10-21: what happened to each item

You accepted R3 (and moved the files), set R6's scope, and accepted everything else.

| Item | Status |
|---|---|
| D1 test hook | Kept; the test docstring now says `vm_stat` is replaced too |
| D2 extras | Kept |
| D3 TDD note | Noted |
| D4 `deepseek-r1:8b` | Kept as the backup reasoning model |
| D5 journal labels | Done: only the four section names remain, sub-labels in my own words |
| D6 opening call | Done: *Load* and *Opening call* added to `GLOSSARY.md`; the report has `load_s`, `opening_call_s`, `loaded_before_run` |
| D7 run coverage | Done: config error if an alias has no case or a case has no check |
| D8 SKILL.md | Done: addresses read from the report, "misrouted", no hard-coded size |
| R1 checks | Done: `tools/check.sh`, `.githooks/pre-commit`, `.github/workflows/checks.yml` (checkout pinned to a commit). **Needs you:** `git config core.hooksPath .githooks` once; CI runs on your next push |
| R2 starting folder | (b) done in SKILL.md; (c) done through R6. **Needs you, optional:** the `gw` shell shortcut in `recover_session_instructions.md` |
| R3 code out of the skill folder | Done: you moved it; I removed the duplicate `skill-staging/` and updated every path |
| R4 review standards | Done: `CODING_STANDARDS.md` at the repo root |
| R5 evidence on disk | Done: `logs/setup.log`; `loaded_before_run` in reports |
| R6 repo-root settings | Done: `.claude/settings.local.json` at the root holds the sandbox network grants, `UV_CACHE_DIR`, and `Edit` deny rules for `raw/{roadmaps,notebooks,assets,README.md}`, the course folders, the course venv and every `.env`. Writes everywhere else in the repo are allowed. The old `litellm/.claude/settings.local.json` is removed. Sessions now start at the repo root |
| R7 uv cache | Done: `UV_CACHE_DIR` set in the settings; `.uv-cache/` is git-ignored |
| N1 ingest and commit | Done: see the git log; the baseline note is in `raw/story-updates/` |
| N2 runner follow-ups | Done: timed load, opening-call misroute check, `loaded_before_run`, constant failure kinds, 120-character lines |
| N3 context drift | Done: the `context_mismatch` warning. Your note is recorded: `OLLAMA_MAX_LOADED_MODELS=1` was set when Ollama started |
| N4 cold-call question | Answered by experiment, from the baseline note: a load within 2 s of an unload takes 5.1–6.4 s, one 5 s or more later about 0.8 s. The runner now waits 5 s. The cause is still a hypothesis |
| N5 course compatibility | The case is added and passes (Responses API with `reasoning_effort: low`). Pointing Perplexia at the gateway is your coursework, which Claude can't write to; the snippet is below |
| N6 frontier alias | **Needs you:** an OpenRouter key with a credit limit, exported as `OPENROUTER_API_KEY` in the gateway's window. This changed from `OPENAI_API_KEY` on 2026-10-21, because your OpenRouter budget covers the calls. The steps are in `recover_session_instructions.md`. Then Claude adds the alias and its cases |
| N7 vllm-metal | Deferred: it needs `brew install` and a model in a vLLM-loadable format. *Proposed:* start it in its own session with `/grill-with-docs` |
| N8 three-model lineup | Future project |
| N9 journal | Done: entry for 2026-10-21 (morning) |

**Two things found along the way:**
- **The second brain's tooling tests were failing** (26 errors on macOS). `Brain` didn't resolve
  its root, and `/tmp` and `/var` are symlinks. Fixed in `tools/brain.py`; all 34 tests now pass.
- **A course dataset prompt nearly went into `cases.yaml`.** I wrote it and replaced it before
  anything was committed. It's now a review rule.

**N5 snippet for Perplexia, if you want Part 1 on the local model:**

```python
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="local-reasoning", base_url="http://127.0.0.1:4000/v1", api_key="sk-local-dev",
                 use_responses_api=True, reasoning_effort="low")
```
