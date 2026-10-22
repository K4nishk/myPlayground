#!/usr/bin/env python3
"""Report words from a GLOSSARY.md's _Avoid_ lists that docs use.

    python3 tools/check_glossary.py --glossary problem_first_ai/litellm/GLOSSARY.md FILE...

Prints one line per use (file:line, the word, the term it is avoided for) and exits 1 when there
is any, 0 otherwise. Code (spans and fenced blocks), link targets, URLs and quoted mentions are
not uses.

Some avoided words are left to review (CODING_STANDARDS.md, "Domain words"), because only a
reader can tell whether they're used in the avoided sense: words that are glossary terms in their
own right, entries that carry a qualifier ('"local" for the NVIDIA hardware'), and the everyday
words below.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

EVERYDAY_WORDS = frozenset({"active", "assertion", "benchmark", "capability", "eval", "hot", "limit",
                            "location", "running", "size", "test"})
TERM = re.compile(r"\*\*(.+?)\*\*:")
NOT_PROSE = [re.compile(p) for p in (r"`[^`]*`", r"\]\([^)]*\)", r"https?://\S+", r'"[^"]*"', r"“[^”]*”")]


def avoided_words(glossary: Path) -> dict[str, str]:
    """Each checkable avoided word, lower-cased, mapped to the term it is avoided for."""
    terms: set[str] = set()
    avoided: dict[str, str] = {}
    term = None
    for line in glossary.read_text().splitlines():
        if match := TERM.match(line):
            term = match.group(1)
            terms.add(term.lower())
        elif line.startswith("_Avoid_:") and term:
            for word in (w.strip() for w in line.removeprefix("_Avoid_:").split(",")):
                if word and '"' not in word:
                    avoided.setdefault(word.lower(), term)
    return {word: term for word, term in avoided.items() if word not in terms | EVERYDAY_WORDS}


def uses(path: Path, avoided: dict[str, str]) -> list[str]:
    found = []
    fenced = False
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        prose = line
        for pattern in NOT_PROSE:
            prose = pattern.sub(" ", prose)
        prose = prose.lower()
        for word, term in avoided.items():
            if re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", prose):
                found.append(f'{path}:{number}: "{word}" is on the _Avoid_ list for **{term}**')
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--glossary", required=True, type=Path, help="the GLOSSARY.md whose _Avoid_ lists apply")
    parser.add_argument("files", nargs="+", type=Path, help="docs to check (the glossary itself is skipped)")
    args = parser.parse_args(argv)
    avoided = avoided_words(args.glossary)
    found = [use for path in args.files if path.resolve() != args.glossary.resolve() for use in uses(path, avoided)]
    if found:
        print("\n".join(found))
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
