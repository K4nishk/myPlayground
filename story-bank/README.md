# story-bank — living project narratives

One story per project, in STAR form (Situation, Task, Action, Result), ready to
turn into a status update, an interview answer, or a résumé bullet. Stories are
**drafted by the agent from the wiki and your updates, and curated by you.**

## How a story grows

```
raw/story-updates/2026-11-02-vllm-knee.md   ← you: what you did + numbers + how measured
        │  /ingest
        ▼
wiki/projects/02-…md   (design + results updated, `updated:` bumped)
        │  lint sees project newer than story → "stale"
        ▼  /heal
story-bank/stories/k8s-vllm-serving.md      ← Action rewritten, TBDs replaced,
                                              evidence: [raw/story-updates/…] added,
                                              last_synced bumped, changelog line
```

Status moves `planned → in-progress → shipped` as evidence arrives.

## Self-healing

`python3 tools/brain.py lint` flags, and `/heal` repairs:

| Problem | Detected by | Healed by |
|---|---|---|
| Story older than its project page | `updated` > `last_synced` | Re-sync Situation/Task/Action from the page |
| A number with no evidence | `shipped` with `evidence: []`; reviewer pass for others | Cite a `raw/story-updates/` file or revert to TBD |
| Broken link / missing project page | link + path checks | Fix the link or retarget the story |
| Missing STAR section or frontmatter | structure checks | Restore from `stories/_template.md` |
| Story missing from the index | index check | Add the row |
| `TBD`s still open | info count | Fill when evidence lands; list in Open threads |

## Rules

1. **No number without evidence.** Every figure in *Result* cites a file in
   `raw/story-updates/`. Plans are written as *Planned*, never as outcomes.
2. **Credit collaborators** by name where their framework or work is used
   (e.g. Aish for the Sovereign AI Engine).
3. **Keep the changelog.** One line per material change, so you can see how a
   story evolved.
4. **No confidential employer detail** in stories unless you add it yourself
   and mark it as OK to use.

## Using it

- `/story <id> <audience>` — refine a story for an audience (status update,
  interview, résumé, LinkedIn) using only what it can cite.
- The index (`index.md`) shows status and open TBDs at a glance.
