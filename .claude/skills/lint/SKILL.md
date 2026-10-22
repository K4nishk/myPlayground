---
name: lint
description: Health-check the second brain — mechanical lint plus a judgement pass for contradictions, stale claims, missing concepts and data gaps. Use when the user asks for a health check, audit, or "what's out of date", or periodically after several ingests.
---

# Lint — report, don't fix

1. `python3 tools/brain.py lint` — mechanical checks (links, frontmatter, index
   coverage, orphans, log format, cited sources, story structure, staleness,
   unbacked results, raw drift).
2. Judgement pass the script can't do — read across pages for:
   - contradictions between pages, or with a newer source;
   - claims a newer source superseded;
   - an idea discussed on 2+ pages without its own concept page;
   - numbers in stories or pages without a citation;
   - questions the wiki can't answer yet → suggest the source to collect.
3. Report grouped by severity with a proposed fix each. Log it:
   `python3 tools/brain.py log lint "<summary>" --note "<n> errors, <n> warnings"`.
4. Offer to run `heal`.
