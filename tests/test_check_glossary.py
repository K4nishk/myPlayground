"""Tests for tools/check_glossary.py at its command line: python3 -m unittest discover -s tests"""

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "check_glossary.py"

GLOSSARY = """\
# Glossary

**Gateway**:
The single front door every client calls.
_Avoid_: router, endpoint

**Opening call**:
The first call to an alias in a run.
_Avoid_: warm-up call, first call

**Case**:
One prompt sent to one alias.
_Avoid_: test query, test

**Backend model**:
The concrete model a backend serves.
_Avoid_: endpoint, alias

**Alias**:
A stable name for a role.
_Avoid_: model name

**Tier**:
Where an alias's backend model runs.
_Avoid_: provider, "frontier" for a model reached through OpenRouter
"""


class CheckGlossary(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.glossary = self.dir / "GLOSSARY.md"
        self.glossary.write_text(GLOSSARY)

    def check(self, text):
        doc = self.dir / "doc.md"
        doc.write_text(textwrap.dedent(text))
        return subprocess.run([sys.executable, str(SCRIPT), "--glossary", str(self.glossary), str(doc)],
                              capture_output=True, text=True)

    def test_an_avoided_word_in_prose_is_reported_with_its_line_and_term(self):
        proc = self.check("""\
            # Notes

            The Router sends each call on.
            """)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("doc.md:3", proc.stdout)
        self.assertIn('"router"', proc.stdout)
        self.assertIn("Gateway", proc.stdout)

    def test_a_document_in_the_glossarys_words_passes(self):
        proc = self.check("The gateway sends the opening call to the backend model.\n")
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_code_link_targets_urls_and_quoted_mentions_are_not_uses(self):
        proc = self.check('''\
            Run `router.py`, see [the gateway](router.md) or https://example.com/endpoint.
            The skill says "first call"; the glossary's term is opening call.

            ```bash
            curl $ENDPOINT  # router
            ```
            ''')
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_words_whose_sense_decides_are_left_to_review(self):
        # "alias" is a term in its own right, "test" is an everyday word, and the "frontier" entry
        # carries a qualifier: only a reader can tell whether each is used in the avoided sense.
        proc = self.check("Each alias has a test, and frontier models answer it.\n")
        self.assertEqual(proc.returncode, 0, proc.stdout)


if __name__ == "__main__":
    unittest.main()
