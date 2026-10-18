# WIKI_SCHEMA — how this second brain is structured and maintained

Pattern: Andrej Karpathy's
[LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).
RAG re-derives knowledge from raw documents on every query. This repo works
the other way: the agent **compiles** sources once into a persistent,
interlinked markdown wiki and keeps it current. Each new source makes the wiki
richer instead of making retrieval noisier.

## Layers

| Layer | Path | Owner | Rule |
|---|---|---|---|
| Raw sources | `raw/` | You | Immutable ground truth. The agent reads, never rewrites. |
| Wiki | `wiki/` | Agent | Compiled knowledge: projects, concepts, notebooks, synthesis. |
| Story bank | `story-bank/` | Agent drafts, you curate | Project narratives (STAR) for updates, reviews, interviews. |
| Schema | `wiki/WIKI_SCHEMA.md`, `CLAUDE.md` | Both | The rules. Changes to it get a `refactor` log entry. |
| Tooling | `tools/brain.py`, `.brain/manifest.json` | Agent | Detects drift, lints health, appends the log. |

## Layout

```
raw/                        you drop sources here (see raw/README.md)
wiki/
  WIKI_SCHEMA.md            this file
  index.md                  catalog of every page: link, one-line summary, metadata
  log.md                    append-only history of ingests, queries, lint, heal
  overview.md               the big picture: how the six projects fit together
  projects/                 01-… through 06-…: architecture + stack per project
  concepts/                 cross-cutting ideas reused by several projects
  notebooks/                analysis + extension plans for learning notebooks
  synthesis/                answers to queries worth keeping (filed back by /query)
story-bank/
  index.md                  catalog of stories with status
  stories/_template.md      STAR template
  stories/<project>.md      one living narrative per project
labs/                       runnable code that wiki pages document
tools/brain.py              status | lint | ingested | log
```

## Page frontmatter

Every wiki page except `index.md`, `log.md` and this file starts with:

```yaml
---
title: KV Cache
type: concept            # overview | project | concept | notebook | synthesis
status: draft            # draft | active | stable | superseded
tags: [inference, memory]
sources: [raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md]   # raw files this page compiles
related: [concepts/continuous-batching.md]                        # optional, wiki-relative
updated: 2026-10-18      # bump on every material edit (drives story staleness)
---
```

Every story starts with:

```yaml
---
id: sovereign-ai-engine
title: Sovereign AI Engine
status: planned          # planned | in-progress | shipped
projects: [wiki/projects/06-sovereign-ai-engine.md]   # repo-relative
last_synced: 2026-10-18  # date the story was last reconciled with its project pages
evidence: []             # raw/story-updates/* files backing every number in Result
---
```

## Writing rules

1. **One idea per page.** Projects link to concepts instead of re-explaining
   them. If a paragraph would be useful from two projects, it is a concept page.
2. **Relative links only**, from the page's own folder
   (`../concepts/kv-cache.md`). `brain.py lint` fails on broken links.
3. **Provenance is visible.** Each page ends with `## Sources`. Inside the page:
   - Facts from your sources link to the `raw/` file.
   - Design the agent proposes beyond your sources is labelled **Proposed**.
   - Example numbers that are not measurements are labelled _illustrative_.
   - **Measured numbers must cite a `raw/story-updates/` file.** No exceptions —
     this is what keeps the story bank honest.
4. **Contradictions are surfaced, not silently resolved.** When a new source
   disagrees with a page, add a `> **Conflict (date):** …` callout citing both
   sources, then resolve it with you.
5. **Status tracks reality.** `draft` = compiled from plans only;
   `active` = being built, has updates; `stable` = shipped and evidenced;
   `superseded` = replaced (link to the successor).

## Operations

### Ingest (`/ingest`) — absorb new or changed raw sources
1. `python3 tools/brain.py status` → list of NEW / CHANGED / REMOVED raw files.
2. Read each source fully. For CHANGED files, `git diff` it to see what moved.
3. Update every affected page — typically several: the project page, the
   concepts it touches, `overview.md`, the matching story. Create pages for new
   concepts. Bump `updated:`.
4. Story updates also flow into `story-bank/` (see Heal step 3).
5. Update `index.md` for any new page or changed summary.
6. `python3 tools/brain.py ingested <files…>` then
   `python3 tools/brain.py log ingest "<title>" --note "<pages touched>"`.
7. `python3 tools/brain.py lint` must report 0 errors.

### Query (`/query`) — answer from the wiki
1. Read `index.md` first, then the relevant pages (not `raw/`, unless a page is
   missing something — then that's an ingest gap to note).
2. Answer with citations as links to wiki pages (and `raw/` files for numbers).
3. If the answer is new synthesis worth keeping (a comparison, a decision, a
   plan), file it as `wiki/synthesis/YYYY-MM-DD-slug.md`, link it from the
   relevant pages and the index, and log `query`.

### Lint (`/lint`) — health check
`brain.py lint` checks mechanically: broken links, missing frontmatter, pages
missing from the index, orphans, log format and ordering, cited sources that
don't exist, story structure, stale stories, unbacked results, pending raw
drift. The agent then checks what a script can't: contradictions between
pages, claims a newer source superseded, concepts mentioned on several pages
that deserve their own page, and gaps worth a new source.

### Heal (`/heal`) — repair everything lint found
1. Fix mechanical errors (links, frontmatter, index entries).
2. Resolve or surface contradictions (rule 4).
3. Re-sync stale stories: re-read their project pages and evidence, rewrite
   Situation/Task/Action from the current design, update Result **only** from
   cited evidence, replace `TBD`s you now have data for, set `last_synced`.
4. Log `heal`.

## index.md format

One table per section (Overview, Projects, Concepts, Notebooks, Synthesis):
`| Page | Summary | Status | Updated |`, with the page as a relative link and a
one-line summary that would let someone decide whether to open it.

## log.md format

Append-only; never edit past entries. Each entry header is exactly:

```
## [YYYY-MM-DD] action | Title
```

`action` ∈ `setup ingest query lint heal refactor`. Bullets beneath list pages
touched. `grep "^## \[" wiki/log.md | tail -5` shows recent activity.
