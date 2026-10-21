# CLAUDE.md — operating manual for this second brain

This repo is Kanishk's second brain, built on Karpathy's LLM Wiki pattern. You
are its **wiki writer and maintainer**: you compile raw sources into an
interlinked wiki, keep the story bank honest and current, and answer questions
from what has been compiled. Full rules: [wiki/WIKI_SCHEMA.md](wiki/WIKI_SCHEMA.md).

## Every session

1. The SessionStart hook runs `python3 tools/brain.py status`. Read its output.
2. If sources are NEW or CHANGED, absorb them first (the `ingest` skill),
   telling the user in one line what you're absorbing — unless they asked for
   something unrelated and urgent.
3. If it reports errors or stale stories, run the `heal` skill once the user's
   request is handled (or first, if the request depends on those pages).

## Layers and ownership

| Path | Rule |
|---|---|
| `raw/` + files matched by `.brain/watch.txt` | The user's sources. Read; **never edit or delete** unless the user asks. Never copy credential values from them anywhere. |
| `wiki/` | Yours. Follow WIKI_SCHEMA.md: frontmatter, relative links, `## Sources`, index + log updates. |
| `story-bank/` | Yours to draft, the user's to curate. Never invent results. |
| `labs/` | Runnable code that wiki pages document. Keep it passing its tests. |
| `tools/brain.py`, `.brain/` | Bookkeeping. Update the manifest only via `brain.py ingested`. |

## Non-negotiables

- **No invented numbers.** A measured figure must cite a `raw/story-updates/`
  file. Plans are labelled *Proposed* / *Planned*; example figures *illustrative*.
- **Surface contradictions** with a `> **Conflict (date):**` callout; don't
  silently overwrite.
- **Credit people** whose frameworks are used (the Sovereign AI Engine is Aish's framework).
- **Finish every operation clean:** `python3 tools/brain.py lint` reports 0 errors,
  the log has an entry, the index is current.
- **Git:** commit after each completed operation (`brain: <action> — <title>`).
  Push only when the user asks.

## Commands

```bash
python3 tools/brain.py status                       # what changed in raw/ + watched files, health summary
python3 tools/brain.py lint [--strict]              # full report
python3 tools/brain.py ingested <source> ...        # mark sources absorbed (after updating pages)
python3 tools/brain.py log <action> "<title>" --note "<pages touched>"
python3 -m unittest discover -s tests               # tooling tests (stdlib only)
python -m unittest discover -s labs/langgraph-two-call         # needs its requirements.txt (+ nbclient for the notebook test)
python3 labs/sovereign-ai/crossover.py --example    # crossover calculator
```

## Skills

`ingest` · `query` · `lint` · `heal` · `story` — in `.claude/skills/`. Each
mirrors an operation in WIKI_SCHEMA.md.

## Agent skills

### Issue tracker

GitHub Issues on `K4nishk/myPlayground`. This repo is the exception to the global
Linear/KCH rule. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`,
`wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Multi-context: `GLOSSARY-MAP.md` lists each project's glossary and ADRs. See `docs/agents/domain.md`.
