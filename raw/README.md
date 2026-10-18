# raw/ — source layer (you write here, the agent reads)

This is the only folder you need to touch. Drop anything here and the second
brain absorbs it on the next session (`/ingest`). The agent **reads** these
files but never rewrites them — they are the ground truth every wiki claim and
story metric traces back to.

| Folder | Put here | Absorbed into |
|---|---|---|
| `roadmaps/` | Project plans, blueprints, roadmap revisions | `wiki/projects/`, `wiki/overview.md` |
| `story-updates/` | Progress notes: what you built, numbers you measured, decisions you made (copy `_TEMPLATE.md`) | `story-bank/stories/`, project pages |
| `notebooks/` | Exported notebooks (`.ipynb`, `.py`) or notes from learning sessions | `wiki/notebooks/` |
| `inbox/` | Anything unsorted: articles, transcripts, screenshots, half-thoughts | wherever it belongs (the agent routes it) |
| `assets/` | Images and diagrams referenced by sources | linked from wiki pages |

Conventions

- Name files `YYYY-MM-DD-short-slug.md` so history sorts naturally.
- Editing a file you already dropped is fine — the change is detected
  (content hash) and the affected pages are re-synced. Prefer a *new* dated
  file for new information, so the history of what you knew when stays intact.
- Files starting with `_` or `.` (templates, `.gitkeep`) are ignored.
- A file that has to live elsewhere (e.g. a notebook beside its `.venv`) can be
  tracked in place: add a glob to `.brain/watch.txt`. Notebooks are compared by
  cell source, so re-running them doesn't count as a change.
- Don't put secrets, credentials, or personal contact details here.
