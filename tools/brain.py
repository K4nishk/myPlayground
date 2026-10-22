#!/usr/bin/env python3
"""Second-brain maintenance CLI.

Deterministic bookkeeping for the LLM-maintained wiki: it detects which
sources have not been absorbed yet, lints the wiki and story bank, and appends
to the log. The LLM does the writing; this script tells it what needs writing.

Sources are everything under raw/ plus any glob listed in .brain/watch.txt
(for files that must stay where they are, e.g. a notebook next to its venv).

Stdlib only, so it runs anywhere python3 does.

    python3 tools/brain.py status             # pending ingests + health summary
    python3 tools/brain.py lint [--strict]    # full report, exit 1 on errors
    python3 tools/brain.py ingested PATH...   # record sources as absorbed
    python3 tools/brain.py log ACTION TITLE   # append "## [date] action | title"
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

LOG_ACTIONS = ("setup", "ingest", "query", "lint", "heal", "refactor")
WIKI_TYPES = ("overview", "project", "concept", "notebook", "synthesis")
WIKI_REQUIRED = ("title", "type", "status", "updated")
STORY_REQUIRED = ("id", "title", "status", "projects", "last_synced", "evidence")
STORY_SECTIONS = ("## Situation", "## Task", "## Action", "## Result")
STORY_STATUSES = ("planned", "in-progress", "shipped")
# Pages that are allowed to exist without frontmatter or inbound links.
WIKI_META = ("index.md", "log.md", "WIKI_SCHEMA.md")

LOG_LINE = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\] (\w+) \| \S.*$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE = re.compile(r"^(```|~~~).*?^\1", re.M | re.S)
INLINE_CODE = re.compile(r"`[^`\n]*`")

# High-precision credential shapes. Matches are reported by kind and length only.
SECRETS = {
    "OpenAI/OpenRouter-style key": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    "Arize-style key": re.compile(r"\bak-[0-9a-f]{8}-[0-9a-f-]{4,}"),
    "GitHub token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"),
    "Hugging Face token": re.compile(r"\bhf_[A-Za-z0-9]{20,}"),
    "LangSmith key": re.compile(r"\blsv2_[A-Za-z0-9_]{20,}"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}
# Code that prints part of an env var, e.g. print(os.environ["API_KEY"][:20]): the next run leaks a prefix.
ENV_SLICE = re.compile(r"os\.(?:environ\[[^\]]+\]|environ\.get\([^)]*\)|getenv\([^)]*\))\s*\[[^\]]*:[^\]]*\]")


@dataclass(frozen=True)
class Issue:
    level: str  # "error" | "warn" | "info"
    path: str
    message: str


def today() -> str:
    return os.environ.get("BRAIN_TODAY") or dt.date.today().isoformat()


# --------------------------------------------------------------------------- #
# Parsing helpers
# --------------------------------------------------------------------------- #

def parse_frontmatter(text: str) -> dict[str, object] | None:
    """Parse a minimal YAML subset: `key: value`, `key: [a, b]`, and `- item` lists."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    data: dict[str, object] = {}
    current_list: list[str] | None = None
    for raw in text[4:end].splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.lstrip().startswith("- ") and current_list is not None:
            current_list.append(_scalar(line.lstrip()[2:]))
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        key, value = key.strip(), value.strip()
        if value == "":
            current_list = []
            data[key] = current_list
        elif value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            data[key] = [_scalar(v) for v in inner.split(",")] if inner else []
            current_list = None
        else:
            data[key] = _scalar(value)
            current_list = None
    return data


def _scalar(value: str) -> str:
    value = value.split(" #", 1)[0].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def body_links(text: str) -> list[str]:
    """Relative link targets in a markdown body, ignoring code and external URLs."""
    text = FENCE.sub("", text)
    text = INLINE_CODE.sub("", text)
    targets = []
    for target in LINK.findall(text):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"):
            continue
        targets.append(target.split("#", 1)[0])
    return [t for t in targets if t]


def link_targets(text: str) -> list[tuple[str, str]]:
    """(path, anchor) for every relative link; path is "" for same-page anchors."""
    text = INLINE_CODE.sub("", FENCE.sub("", text))
    out = []
    for target in LINK.findall(text):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
            continue
        path, _, anchor = target.partition("#")
        out.append((path, anchor))
    return out


def anchors(text: str) -> set[str]:
    """GitHub-style heading slugs, including -1, -2 suffixes for duplicates."""
    seen: dict[str, int] = {}
    for line in FENCE.sub("", text).splitlines():
        match = re.match(r"^#{1,6}\s+(.*?)\s*#*\s*$", line)
        if not match:
            continue
        slug = re.sub(r"[^\w\- ]", "", match.group(1).strip().lower()).replace(" ", "-")
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        if count:
            seen[f"{slug}-{count}"] = 1
    return set(seen)


def notebook_text(raw: bytes) -> str | None:
    """Cell types + sources of a .ipynb, ignoring outputs and execution counts."""
    try:
        cells = json.loads(raw)["cells"]
    except (ValueError, KeyError, TypeError):
        return None
    return json.dumps([(c.get("cell_type"), "".join(c.get("source", ""))) for c in cells])


def find_secrets(text: str) -> list[tuple[str, int]]:
    return [(kind, len(m.group(0))) for kind, rx in SECRETS.items() for m in rx.finditer(text)]


def notebook_secrets(raw: bytes) -> list[tuple[str, str, int]] | None:
    """(where, kind, length) per credential-shaped string in a notebook's cells."""
    try:
        cells = json.loads(raw)["cells"]
    except (ValueError, KeyError, TypeError):
        return None
    hits = []
    for i, cell in enumerate(cells):
        source = "".join(cell.get("source", ""))
        parts = {"source": source, "output": json.dumps(cell.get("outputs", []))}
        for where, text in parts.items():
            hits += [(f"cell {i} {where}", kind, n) for kind, n in find_secrets(text)]
        if cell.get("cell_type") == "code":
            live = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))
            hits += [(f"cell {i} source", "code that prints a slice of an env var", len(m.group(0)))
                     for m in ENV_SLICE.finditer(live)]
    return hits


def as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [str(value)]


# --------------------------------------------------------------------------- #
# The brain
# --------------------------------------------------------------------------- #

class Brain:
    def __init__(self, root: Path):
        self.root = root
        self.raw = root / "raw"
        self.wiki = root / "wiki"
        self.stories = root / "story-bank"
        self.manifest_path = root / ".brain" / "manifest.json"
        self.watch_path = root / ".brain" / "watch.txt"

    def rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    # ----- source drift ----------------------------------------------------- #

    @staticmethod
    def _visible(path: Path, base: Path) -> bool:
        """Skip templates, READMEs, and anything under a hidden or _ folder (.venv, checkpoints)."""
        return path.is_file() and path.name != "README.md" and not any(
            part.startswith((".", "_")) for part in path.relative_to(base).parts)

    def watch_globs(self) -> list[str]:
        if not self.watch_path.exists():
            return []
        lines = (line.split("#", 1)[0].strip() for line in self.watch_path.read_text().splitlines())
        return [line for line in lines if line]

    def source_files(self) -> list[Path]:
        files = set(p for p in self.raw.rglob("*") if self._visible(p, self.raw)) if self.raw.exists() else set()
        for pattern in self.watch_globs():
            files.update(p for p in self.root.glob(pattern) if self._visible(p, self.root))
        return sorted(files)

    def load_manifest(self) -> dict:
        if not self.manifest_path.exists():
            return {"sources": {}}
        return json.loads(self.manifest_path.read_text())

    def save_manifest(self, manifest: dict) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest["sources"] = dict(sorted(manifest["sources"].items()))
        self.manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    @staticmethod
    def digest(path: Path) -> str:
        """Content hash. Notebooks hash cell sources only, so re-running cells isn't a change."""
        raw = path.read_bytes()
        if path.suffix == ".ipynb" and (text := notebook_text(raw)) is not None:
            raw = text.encode()
        return hashlib.sha256(raw).hexdigest()

    def drift(self) -> dict[str, list[str]]:
        tracked = self.load_manifest()["sources"]
        current = {self.rel(p): p for p in self.source_files()}
        new, changed = [], []
        for rel, path in current.items():
            if rel not in tracked:
                new.append(rel)
            elif tracked[rel]["sha256"] != self.digest(path):
                changed.append(rel)
        removed = sorted(set(tracked) - set(current))
        return {"new": new, "changed": changed, "removed": removed}

    def mark_ingested(self, paths: list[str]) -> list[str]:
        manifest = self.load_manifest()
        sources = {p.resolve() for p in self.source_files()}
        recorded = []
        for arg in paths:
            path = Path(arg).resolve()
            if not path.exists():
                path = (self.root / arg).resolve()
            if path not in sources:
                raise SystemExit(f"not a tracked source (raw/ or .brain/watch.txt): {arg}")
            rel = self.rel(path)
            manifest["sources"][rel] = {"sha256": self.digest(path), "ingested": today()}
            recorded.append(rel)
        for rel in self.drift()["removed"]:
            manifest["sources"].pop(rel, None)
        self.save_manifest(manifest)
        return recorded

    # ----- lint ------------------------------------------------------------- #

    def wiki_pages(self) -> list[Path]:
        return sorted(self.wiki.rglob("*.md")) if self.wiki.exists() else []

    def story_pages(self) -> list[Path]:
        folder = self.stories / "stories"
        if not folder.exists():
            return []
        return sorted(p for p in folder.glob("*.md") if not p.name.startswith("_"))

    def lint(self, include_drift: bool = True) -> list[Issue]:
        issues: list[Issue] = []
        issues += self._lint_links()
        issues += self._lint_wiki()
        issues += self._lint_log()
        issues += self._lint_stories()
        issues += self._lint_secrets()
        if not include_drift:
            return issues
        drift = self.drift()
        for kind in ("new", "changed"):
            for rel in drift[kind]:
                issues.append(Issue("warn", rel, f"source is {kind}; run /ingest"))
        for rel in drift["removed"]:
            issues.append(Issue("warn", rel, "source was deleted; check pages that cite it"))
        return issues

    def _markdown_files(self) -> list[Path]:
        files = self.wiki_pages()
        if self.stories.exists():
            files += sorted(self.stories.rglob("*.md"))
        for extra in ("README.md", "CLAUDE.md"):
            if (self.root / extra).exists():
                files.append(self.root / extra)
        return files

    def _lint_secrets(self) -> list[Issue]:
        """Credentials must never reach the wiki (error); in your own sources they're a warning."""
        issues = []
        for path in self.source_files():
            raw = path.read_bytes()
            hits = notebook_secrets(raw) if path.suffix == ".ipynb" else None
            if hits is None:
                hits = [("", kind, n) for kind, n in find_secrets(raw.decode(errors="ignore"))]
            for where, kind, n in hits:
                at = f" in {where}" if where else ""
                if kind.startswith("code that"):
                    message = f"{where}: {kind}; print whether it is set and its length instead"
                else:
                    message = f"possible credential{at} ({kind}, {n} chars): rotate it, then remove it"
                issues.append(Issue("warn", self.rel(path), message))
        for page in self._markdown_files():
            for kind, n in find_secrets(page.read_text()):
                issues.append(Issue("error", self.rel(page), f"credential-shaped string ({kind}, {n} chars)"))
        return issues

    def _lint_links(self) -> list[Issue]:
        issues = []
        for page in self._markdown_files():
            for path, anchor in link_targets(page.read_text()):
                target = (page.parent / path).resolve() if path else page
                shown = f"{path}#{anchor}" if anchor else path
                if not target.exists():
                    issues.append(Issue("error", self.rel(page), f"broken link -> {shown}"))
                elif anchor and target.suffix == ".md" and anchor not in anchors(target.read_text()):
                    issues.append(Issue("error", self.rel(page), f"broken anchor -> {shown}"))
        return issues

    def _lint_wiki(self) -> list[Issue]:
        issues = []
        pages = [p for p in self.wiki_pages() if p.name not in WIKI_META or p.parent != self.wiki]
        index = self.wiki / "index.md"
        index_targets = set()
        if index.exists():
            index_targets = {(index.parent / t).resolve() for t in body_links(index.read_text())}
        else:
            issues.append(Issue("error", "wiki/index.md", "missing index"))

        inbound: dict[Path, int] = {p.resolve(): 0 for p in pages}
        for page in self.wiki_pages():
            if page.parent == self.wiki and page.name in ("index.md", "log.md"):
                continue
            for target in body_links(page.read_text()):
                resolved = (page.parent / target).resolve()
                if resolved in inbound and resolved != page.resolve():
                    inbound[resolved] += 1

        for page in pages:
            rel = self.rel(page)
            fm = parse_frontmatter(page.read_text())
            if fm is None:
                issues.append(Issue("error", rel, "missing frontmatter"))
            else:
                for key in WIKI_REQUIRED:
                    if key not in fm:
                        issues.append(Issue("error", rel, f"frontmatter missing '{key}'"))
                if fm.get("type") and fm["type"] not in WIKI_TYPES:
                    issues.append(Issue("error", rel, f"unknown type '{fm['type']}'"))
                if fm.get("updated") and not DATE.match(str(fm["updated"])):
                    issues.append(Issue("error", rel, "'updated' must be YYYY-MM-DD"))
                for src in as_list(fm.get("sources")):
                    if not (self.root / src).exists():
                        issues.append(Issue("error", rel, f"cited source not found: {src}"))
            if page.resolve() not in index_targets:
                issues.append(Issue("error", rel, "not listed in wiki/index.md"))
            if inbound[page.resolve()] == 0:
                issues.append(Issue("warn", rel, "orphan: no inbound links from other wiki pages"))
        return issues

    def _lint_log(self) -> list[Issue]:
        log = self.wiki / "log.md"
        if not log.exists():
            return [Issue("error", "wiki/log.md", "missing log")]
        issues, last = [], ""
        for n, line in enumerate(log.read_text().splitlines(), 1):
            if not line.startswith("## "):
                continue
            match = LOG_LINE.match(line)
            if not match:
                issues.append(Issue("error", f"wiki/log.md:{n}", "entry must be '## [YYYY-MM-DD] action | Title'"))
                continue
            date, action = match.groups()
            if action not in LOG_ACTIONS:
                issues.append(Issue("error", f"wiki/log.md:{n}", f"unknown action '{action}'"))
            if date < last:
                issues.append(Issue("error", f"wiki/log.md:{n}", "out of order: log is append-only"))
            last = max(last, date)
        return issues

    def _lint_stories(self) -> list[Issue]:
        issues = []
        stories = self.story_pages()
        index = self.stories / "index.md"
        listed = set()
        if index.exists():
            listed = {(index.parent / t).resolve() for t in body_links(index.read_text())}
        elif stories:
            issues.append(Issue("error", "story-bank/index.md", "missing story index"))

        for story in stories:
            rel = self.rel(story)
            text = story.read_text()
            fm = parse_frontmatter(text)
            if fm is None:
                issues.append(Issue("error", rel, "missing frontmatter"))
                continue
            for key in STORY_REQUIRED:
                if key not in fm:
                    issues.append(Issue("error", rel, f"frontmatter missing '{key}'"))
            if fm.get("status") and fm["status"] not in STORY_STATUSES:
                issues.append(Issue("error", rel, f"unknown status '{fm['status']}'"))
            for section in STORY_SECTIONS:
                if not re.search(rf"^{re.escape(section)}\b", text, re.M):
                    issues.append(Issue("error", rel, f"missing section '{section}'"))
            if story.resolve() not in listed:
                issues.append(Issue("error", rel, "not listed in story-bank/index.md"))

            synced = str(fm.get("last_synced", ""))
            for project in as_list(fm.get("projects")):
                page = self.root / project
                if not page.exists():
                    issues.append(Issue("error", rel, f"project page not found: {project}"))
                    continue
                pfm = parse_frontmatter(page.read_text()) or {}
                if str(pfm.get("updated", "")) > synced:
                    issues.append(Issue("warn", rel, f"stale: {project} updated after last_synced; run /heal"))
            evidence = as_list(fm.get("evidence"))
            for src in evidence:
                if not (self.root / src).exists():
                    issues.append(Issue("error", rel, f"evidence not found: {src}"))
            if fm.get("status") == "shipped" and not evidence:
                issues.append(Issue("warn", rel, "shipped story has no evidence backing its results"))
            placeholders = len(re.findall(r"\bTBD\b", text))
            if placeholders:
                issues.append(Issue("info", rel, f"{placeholders} TBD placeholder(s) awaiting real data"))
        return issues


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def counts(issues: list[Issue]) -> dict[str, int]:
    return {lvl: sum(i.level == lvl for i in issues) for lvl in ("error", "warn", "info")}


def cmd_status(brain: Brain, _args) -> int:
    drift = brain.drift()
    issues = brain.lint(include_drift=False)
    c = counts(issues)
    stale = sum("stale:" in i.message for i in issues)
    pending = drift["new"] + drift["changed"]

    print(f"Second brain status ({today()})")
    tracked = len(brain.load_manifest()["sources"])
    print(f"  sources: {tracked} absorbed, {len(drift['new'])} new, "
          f"{len(drift['changed'])} changed, {len(drift['removed'])} removed")
    for kind in ("new", "changed", "removed"):
        for rel in drift[kind]:
            print(f"    {kind.upper():8} {rel}")
    print(f"  health: {c['error']} errors, {c['warn']} warnings, {stale} stale stories")

    steps = []
    if pending or drift["removed"]:
        steps.append("/ingest to absorb source changes")
    if stale or c["error"]:
        steps.append("/heal to repair the wiki and story bank")
    print("  next: " + ("; ".join(steps) if steps else "nothing pending — ask away (/query)"))
    return 0


def cmd_lint(brain: Brain, args) -> int:
    issues = brain.lint()
    order = {"error": 0, "warn": 1, "info": 2}
    for issue in sorted(issues, key=lambda i: (order[i.level], i.path)):
        print(f"{issue.level.upper():5} {issue.path}: {issue.message}")
    c = counts(issues)
    print(f"\n{c['error']} errors, {c['warn']} warnings, {c['info']} info")
    return 1 if c["error"] or (args.strict and c["warn"]) else 0


def cmd_ingested(brain: Brain, args) -> int:
    for rel in brain.mark_ingested(args.paths):
        print(f"absorbed {rel}")
    return 0


def cmd_log(brain: Brain, args) -> int:
    if args.action not in LOG_ACTIONS:
        raise SystemExit(f"action must be one of {', '.join(LOG_ACTIONS)}")
    log = brain.wiki / "log.md"
    text = log.read_text() if log.exists() else "# Log\n"
    entry = f"\n## [{today()}] {args.action} | {args.title}\n"
    for note in args.note or []:
        entry += f"- {note}\n"
    log.write_text(text.rstrip("\n") + "\n" + entry)
    print(entry.strip())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="repository root (default: parent of tools/)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="pending ingests and health summary")
    lint = sub.add_parser("lint", help="full health report")
    lint.add_argument("--strict", action="store_true", help="treat warnings as failures")
    ing = sub.add_parser("ingested", help="record sources as absorbed")
    ing.add_argument("paths", nargs="+")
    log = sub.add_parser("log", help="append an entry to wiki/log.md")
    log.add_argument("action")
    log.add_argument("title")
    log.add_argument("--note", action="append", help="bullet line under the entry (repeatable)")
    args = parser.parse_args(argv)

    brain = Brain(args.root.resolve())
    handlers = {"status": cmd_status, "lint": cmd_lint, "ingested": cmd_ingested, "log": cmd_log}
    return handlers[args.cmd](brain, args)


if __name__ == "__main__":
    sys.exit(main())
