---
name: heal
description: Repair everything lint found in the wiki and story bank — broken links, missing frontmatter or index rows, stale stories, unbacked numbers, contradictions. Use when status/lint reports errors or stale stories, or the user says "heal", "fix the wiki", "sync my stories".
---

# Heal — repair the wiki and re-sync the story bank

1. `python3 tools/brain.py lint` to get the work list.
2. Mechanical fixes: broken links (find the moved page; don't delete the link
   blindly), frontmatter, missing index rows, log format.
3. Contradictions: add/resolve `Conflict` callouts; ask the user when the
   sources genuinely disagree.
4. Stale stories (project page `updated` > story `last_synced`), for each:
   - Re-read the project page(s) and every file in `evidence:`.
   - Rewrite Situation / Task / Action to match the current design and what was
     actually done (Planned vs done stays explicit).
   - Result: only figures from cited evidence; anything else stays TBD.
   - Refresh the Angles (status update, STAR, résumé bullet) from the new content.
   - Bump `last_synced`, add a changelog line, update the row in `story-bank/index.md`.
5. Unbacked numbers: cite the evidence file or revert the number to TBD and
   note it under Open threads.
6. `python3 tools/brain.py log heal "<summary>" --note "<what changed>"`;
   lint must be 0 errors; commit `brain: heal — <summary>`.
