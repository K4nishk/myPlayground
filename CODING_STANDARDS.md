# Coding standards

Read during review (`/code-review`), not while implementing. These are judgement calls;
anything mechanical is a check in `tools/check.sh`, which the pre-commit hook and CI run.

## Claims need evidence

A statement about how a dependency, a service or the machine behaves needs a test or a cited
observation behind it. This applies wherever the statement appears: a code comment, a test name
or docstring, a journal entry, a note. Without evidence, it is labelled a hypothesis. Flag any
unlabelled claim the change can't back.

## Numbers need a source

A measured figure cites a `raw/story-updates/` note (see `CLAUDE.md`). Example figures are
labelled illustrative, and plans are labelled *Proposed* or *Planned*. This covers READMEs,
skills and journals as well as the wiki.

## Domain words

Code and docs under `problem_first_ai/litellm/` use the terms in its `GLOSSARY.md` and avoid the
words on its _Avoid_ lists. A new concept gets a glossary entry before it gets a second name.

## Read like the neighbours

New code matches the surrounding code's comment density, naming and idiom. For Python, that's
the labs style (`labs/sovereign-ai/crossover.py`): `from __future__ import annotations`, type
hints, constants at the top, and `parser = argparse.ArgumentParser(description=__doc__, ...)`.

## Tests at agreed seams

Tests exercise a public interface (a command line, an HTTP API). Stand-ins replace only a system
boundary (the network, an OS command), and a new seam is agreed before tests are written at it.

## Course material stays private

Nothing from `problem_first_ai/preread/` or `problem_first_ai/Assignment 1/` is copied into a
tracked file: no dataset rows, no question text, no starter code.
