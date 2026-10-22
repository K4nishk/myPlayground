---
name: story
description: Refine a project story from the story bank for a specific audience — status update, interview STAR answer, résumé bullet, LinkedIn post — using only cited facts. Use when the user wants to write up, pitch, or practise telling a project, or says "refine my story", "project update", "how do I talk about X".
---

# Story — refine a narrative for an audience

Arguments: `<story id> [audience]` (audience: status | interview | resume | linkedin | custom).

1. Read `story-bank/stories/<id>.md`, its project page(s), and every evidence
   file. If lint says it's stale, heal it first.
2. Draft for the audience:
   - **status:** 3 lines — done, next, blocked/asks.
   - **interview:** ~2-minute STAR; lead with the problem; one decision with its
     trade-off; end on the number (or say honestly what's still being measured).
   - **resume:** 1–2 bullets, verb-first, one number each — cited numbers only.
   - **linkedin:** a short post with one insight the reader can reuse.
3. Every figure must come from `evidence:`. Missing data → keep TBD and tell the
   user the single measurement that would most strengthen the story.
4. If the user approves wording, save it into the story's Angles section, add a
   changelog line, bump `last_synced` if you re-read the project, log `heal`
   (`"story refined: <id>"`), lint, commit.
