---
name: ingest
description: Absorb new or changed sources (raw/ plus globs in .brain/watch.txt) into the wiki and story bank. Use when brain.py status shows NEW/CHANGED/REMOVED raw sources, when the user drops or edits a file in raw/, or says "ingest", "absorb", "I added notes", "update the wiki from this".
---

# Ingest — compile raw sources into the wiki

1. Run `python3 tools/brain.py status`. Work through every NEW, CHANGED and
   REMOVED file. If lint reports a possible credential in a source, tell the
   user (kind + location only) and never copy that content into the wiki. For CHANGED, `git diff -- <file>` (or compare against what the
   wiki says) to see exactly what moved.
2. Read each source in full. Briefly tell the user the key takeaways and which
   pages you'll touch (one short list).
3. Update the wiki per `wiki/WIKI_SCHEMA.md`:
   - The project page(s) the source is about — design changes, decisions,
     results (with citation), status (`draft → active → stable`).
   - Every concept page the source adds to; create a concept page when an idea
     now appears on two or more pages.
   - `wiki/overview.md` if the big picture or "where things stand" changed.
   - `wiki/notebooks/` for notebook exports: diff against the extension plan and
     re-target the next steps to where the user actually is.
   - Contradiction with existing content → `> **Conflict (YYYY-MM-DD):**` callout citing both.
   - Bump `updated:` on every page you materially change; add the source to its `sources:`.
4. Story updates (`raw/story-updates/`): update the matching story in
   `story-bank/stories/` — replace TBDs with the measured numbers, add the file
   to `evidence:`, adjust `status`, bump `last_synced`, add a changelog line.
5. REMOVED sources: find pages citing them (`grep -r <path> wiki story-bank`),
   ask the user whether the claims still stand, mark or remove accordingly.
6. Update `wiki/index.md` rows (new pages, changed summaries/status/dates).
7. Bookkeeping:
   ```bash
   python3 tools/brain.py ingested <source> [...]
   python3 tools/brain.py log ingest "<source title>" --note "touched: <pages>"
   python3 tools/brain.py lint      # must be 0 errors
   ```
8. Commit: `brain: ingest — <source title>`. Summarise for the user what the
   brain now knows that it didn't before.
