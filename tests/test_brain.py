"""Tests for tools/brain.py: python3 -m unittest discover -s tests"""

import io
import os
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import brain  # noqa: E402

os.environ["BRAIN_TODAY"] = "2026-10-18"

PAGE = """---
title: {title}
type: {type}
status: draft
sources: [raw/notes/a.md]
updated: {updated}
---

# {title}

{body}
"""

STORY = """---
id: s
title: S
status: {status}
projects: [wiki/projects/p.md]
last_synced: {synced}
evidence: [{evidence}]
---

# S

## Situation
x
## Task
x
## Action
x
## Result
{result}
"""


class BrainFixture(unittest.TestCase):
    """A minimal healthy brain in a temp dir; tests break one thing at a time."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.write("raw/notes/a.md", "source A")
        self.write("raw/_TEMPLATE.md", "ignored")
        self.write("wiki/index.md", "[P](projects/p.md) [C](concepts/c.md)")
        self.write("wiki/log.md", "# Log\n\n## [2026-10-17] setup | Start\n")
        self.write("wiki/projects/p.md", PAGE.format(
            title="P", type="project", updated="2026-10-18", body="See [C](../concepts/c.md#details)."))
        self.write("wiki/concepts/c.md", PAGE.format(
            title="C", type="concept", updated="2026-10-18", body="Back to [P](../projects/p.md).\n\n## Details\n"))
        self.write("story-bank/index.md", "[S](stories/s.md)")
        self.write("story-bank/stories/s.md", STORY.format(
            status="planned", synced="2026-10-18", evidence="", result="TBD"))
        self.brain = brain.Brain(self.root)
        self.brain.mark_ingested([str(self.root / "raw/notes/a.md")])

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text))

    def messages(self, level=None):
        return [f"{i.path}: {i.message}" for i in self.brain.lint() if level in (None, i.level)]

    def assertFlags(self, fragment, level="error"):
        found = self.messages(level)
        self.assertTrue(any(fragment in m for m in found), f"{fragment!r} not in {found}")


class Healthy(BrainFixture):
    def test_fixture_is_clean(self):
        self.assertEqual(self.messages("error") + self.messages("warn"), [])

    def test_tbd_is_reported_as_info(self):
        self.assertFlags("1 TBD placeholder", level="info")


class Drift(BrainFixture):
    def test_new_changed_removed(self):
        self.write("raw/notes/b.md", "new")
        self.write("raw/notes/a.md", "edited")
        self.assertEqual(self.brain.drift(), {"new": ["raw/notes/b.md"], "changed": ["raw/notes/a.md"], "removed": []})
        (self.root / "raw/notes/a.md").unlink()
        self.assertEqual(self.brain.drift()["removed"], ["raw/notes/a.md"])

    def test_templates_and_readmes_ignored(self):
        self.write("raw/README.md", "docs")
        self.write("raw/inbox/.gitkeep", "")
        self.assertEqual(self.brain.drift()["new"], [])

    def test_ingested_clears_drift_and_forgets_removed(self):
        self.write("raw/notes/b.md", "new")
        (self.root / "raw/notes/a.md").unlink()
        self.brain.mark_ingested([str(self.root / "raw/notes/b.md")])
        self.assertEqual(self.brain.drift(), {"new": [], "changed": [], "removed": []})

    def test_ingested_rejects_paths_outside_raw(self):
        with self.assertRaises(SystemExit):
            self.brain.mark_ingested([str(self.root / "wiki/index.md")])

    def test_drift_is_a_lint_warning(self):
        self.write("raw/notes/b.md", "new")
        self.assertFlags("source is new", level="warn")


class WatchedSources(BrainFixture):
    NB = '{"cells": [{"cell_type": "code", "source": ["print(1)"], "outputs": %s}], "metadata": {}}'

    def setUp(self):
        super().setUp()
        self.write(".brain/watch.txt", "# comment\nlab/*.ipynb\n")
        self.write("lab/demo.ipynb", self.NB % "[]")
        self.write("lab/.venv/lib/other.ipynb", self.NB % "[]")

    def test_watched_glob_is_a_source_and_hidden_dirs_are_skipped(self):
        self.assertEqual(self.brain.drift()["new"], ["lab/demo.ipynb"])

    def test_rerunning_a_notebook_is_not_a_change(self):
        self.brain.mark_ingested(["lab/demo.ipynb"])
        self.write("lab/demo.ipynb", self.NB % '[{"output_type": "stream", "text": ["1"]}]')
        self.assertEqual(self.brain.drift()["changed"], [])
        self.write("lab/demo.ipynb", self.NB.replace("print(1)", "print(2)") % "[]")
        self.assertEqual(self.brain.drift()["changed"], ["lab/demo.ipynb"])

    def test_untracked_paths_are_rejected(self):
        with self.assertRaises(SystemExit):
            self.brain.mark_ingested(["lab/.venv/lib/other.ipynb"])


class SecretChecks(BrainFixture):
    KEY = "sk-or-v1-" + "0123456789abcdef" * 4

    def test_credential_in_notebook_output_is_a_warning_with_location(self):
        self.write(".brain/watch.txt", "lab/*.ipynb\n")
        out = '[{"output_type": "stream", "text": ["KEY: %s"]}]' % self.KEY[:20]
        self.write("lab/demo.ipynb", WatchedSources.NB % out)
        self.assertFlags("possible credential in cell 0 output", level="warn")
        self.assertFalse(any(self.KEY[:12] in m for m in self.messages()), "never echo the value")

    def test_code_that_slices_env_vars_is_flagged_before_it_runs(self):
        self.write(".brain/watch.txt", "lab/*.ipynb\n")
        cell = 'print(os.environ[\\"KEY\\"][:20])\\n# print(os.getenv(\\"OLD\\")[:5])'
        self.write("lab/demo.ipynb", WatchedSources.NB.replace("print(1)", cell) % "[]")
        found = [m for m in self.messages("warn") if "slice of an env var" in m]
        self.assertEqual(len(found), 1, found)      # the commented-out line is ignored

    def test_credential_in_wiki_is_an_error(self):
        self.write("wiki/concepts/c.md", PAGE.format(
            title="C", type="concept", updated="2026-10-18", body=f"[P](../projects/p.md) {self.KEY}"))
        self.assertFlags("credential-shaped string")


class WikiChecks(BrainFixture):
    def test_broken_link(self):
        self.write("wiki/concepts/c.md", PAGE.format(
            title="C", type="concept", updated="2026-10-18", body="[gone](../projects/nope.md) [P](../projects/p.md)"))
        self.assertFlags("broken link -> ../projects/nope.md")

    def test_broken_anchor(self):
        self.write("wiki/projects/p.md", PAGE.format(
            title="P", type="project", updated="2026-10-18", body="[C](../concepts/c.md#nope)"))
        self.assertFlags("broken anchor -> ../concepts/c.md#nope")

    def test_links_in_code_are_ignored(self):
        self.write("wiki/projects/p.md", PAGE.format(
            title="P", type="project", updated="2026-10-18",
            body="[C](../concepts/c.md)\n\n```md\n[x](missing.md)\n```\n`[y](missing.md)`"))
        self.assertEqual(self.messages("error"), [])

    def test_page_missing_from_index(self):
        self.write("wiki/concepts/d.md", PAGE.format(
            title="D", type="concept", updated="2026-10-18", body="[P](../projects/p.md)"))
        self.assertFlags("wiki/concepts/d.md: not listed in wiki/index.md")
        self.assertFlags("wiki/concepts/d.md: orphan", level="warn")

    def test_frontmatter_rules(self):
        self.write("wiki/projects/p.md", "---\ntitle: P\ntype: blog\nupdated: Oct 18\n---\n[C](../concepts/c.md)")
        self.assertFlags("frontmatter missing 'status'")
        self.assertFlags("unknown type 'blog'")
        self.assertFlags("'updated' must be YYYY-MM-DD")

    def test_cited_source_must_exist(self):
        (self.root / "raw/notes/a.md").unlink()
        self.assertFlags("cited source not found: raw/notes/a.md")

    def test_log_format_and_order(self):
        self.write("wiki/log.md", "# Log\n\n## [2026-10-18] ingest | B\n\n## [2026-10-17] ingest | A\n\n## bad entry\n")
        self.assertFlags("out of order")
        self.assertFlags("entry must be")

    def test_log_command_appends(self):
        with redirect_stdout(io.StringIO()):
            brain.main(["--root", str(self.root), "log", "query", "What is X?", "--note", "filed: y"])
        self.assertTrue((self.root / "wiki/log.md").read_text().endswith(
            "## [2026-10-18] query | What is X?\n- filed: y\n"))
        self.assertEqual(self.messages("error"), [])


class StoryChecks(BrainFixture):
    def test_stale_when_project_updated_after_sync(self):
        self.write("story-bank/stories/s.md", STORY.format(
            status="planned", synced="2026-10-01", evidence="", result="TBD"))
        self.assertFlags("stale: wiki/projects/p.md", level="warn")

    def test_shipped_without_evidence(self):
        self.write("story-bank/stories/s.md", STORY.format(
            status="shipped", synced="2026-10-18", evidence="", result="Cut latency 40%."))
        self.assertFlags("shipped story has no evidence", level="warn")

    def test_evidence_must_exist(self):
        self.write("story-bank/stories/s.md", STORY.format(
            status="shipped", synced="2026-10-18", evidence="raw/story-updates/x.md", result="40%"))
        self.assertFlags("evidence not found: raw/story-updates/x.md")

    def test_missing_star_section(self):
        text = STORY.format(status="planned", synced="2026-10-18", evidence="", result="TBD")
        self.write("story-bank/stories/s.md", text.replace("## Task\nx\n", ""))
        self.assertFlags("missing section '## Task'")

    def test_story_missing_from_index(self):
        self.write("story-bank/index.md", "nothing listed")
        self.assertFlags("not listed in story-bank/index.md")


class Parsing(unittest.TestCase):
    def test_frontmatter_lists(self):
        fm = brain.parse_frontmatter("---\na: [x, 'y']\nb:\n  - z\nc: plain # comment\nd: []\n---\n")
        self.assertEqual(fm, {"a": ["x", "y"], "b": ["z"], "c": "plain", "d": []})

    def test_anchor_slugs(self):
        slugs = brain.anchors("# Step 7 — Loop on the critique (reflection)\n## Notes\n## Notes\n")
        self.assertIn("step-7--loop-on-the-critique-reflection", slugs)
        self.assertIn("notes-1", slugs)


@unittest.skipIf(os.environ.get("CI"), "a clean checkout lacks the git-ignored course material the wiki "
                 "cites; tools/check.sh skips the brain lint in CI for the same reason")
class ThisRepo(unittest.TestCase):
    def test_repository_lints_without_errors(self):
        errors = [i for i in brain.Brain(ROOT).lint() if i.level == "error"]
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
