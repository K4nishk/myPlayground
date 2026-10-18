---
name: query
description: Answer a question from the compiled wiki with citations, and file valuable answers back as synthesis pages. Use for any question about the user's projects, concepts, plans, trade-offs or progress, or when they want to brainstorm or "churn ideas" against what they already know.
---

# Query — answer from the wiki, compound the answer

1. Read `wiki/index.md`, then the pages it points to. Prefer compiled pages over
   `raw/`; go to `raw/` only for exact figures or when a page is missing
   something — and note that as an ingest gap.
2. Answer directly. Cite as relative links to wiki pages (and `raw/` files for
   numbers). Separate what the wiki says from your own new reasoning, and label
   speculation.
3. When brainstorming, push back: name the weakest assumption, the measurement
   that would settle it, and which project page it affects.
4. If the answer is new synthesis worth keeping (a comparison, decision,
   design, plan), file it:
   - `wiki/synthesis/YYYY-MM-DD-<slug>.md` with `type: synthesis` frontmatter and `## Sources`.
   - Link it from the pages it relates to and add a row to the Synthesis table in `wiki/index.md`.
   - `python3 tools/brain.py log query "<question, short>" --note "filed: <page>"`
   - `python3 tools/brain.py lint`, then commit `brain: query — <title>`.
   Quick factual answers don't need filing; log nothing for those.
