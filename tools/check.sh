#!/usr/bin/env bash
# The repo's checks in one place, run by the pre-commit hook (.githooks/pre-commit) and by CI
# (.github/workflows/checks.yml). Stops at the first failure.
#
#   tools/check.sh            # every check
#   tools/check.sh --staged   # only the checks whose files are staged (what the hook runs)
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

mode="${1:-all}"
step() { printf '== %s\n' "$1"; }

# True when running every check, or when a staged path starts with one of the given prefixes.
changed() {
  [ "$mode" != "--staged" ] && return 0
  git diff --cached --name-only | grep -qE "^($1)"
}

if [ -n "${CI:-}" ]; then
  step "brain lint: skipped in CI (the wiki cites course material that git ignores)"
else
  step "brain lint"
  out=$(python3 tools/brain.py lint) || { echo "$out"; exit 1; }
fi

if changed "tools/|tests/"; then
  step "brain tooling tests"
  python3 -m unittest discover -s tests -q
fi

step "no two ADRs in one docs/adr/ share a number"
# Sessions working in parallel can each take the next number; keep the folder and the number.
dupes=$(git ls-files '*docs/adr/[0-9][0-9][0-9][0-9]-*.md' | sed -E 's#-[^/]*$##' | sort | uniq -d)
if [ -n "$dupes" ]; then
  echo "ADR numbers used twice: $dupes"
  exit 1
fi

if changed "problem_first_ai/litellm/|.claude/skills/local-model-e2e-validator/|tools/check_glossary.py"; then
  step "gateway docs use the glossary's words"
  git ls-files -z 'problem_first_ai/litellm/*.md' '.claude/skills/local-model-e2e-validator/SKILL.md' \
    | xargs -0 python3 tools/check_glossary.py --glossary problem_first_ai/litellm/GLOSSARY.md
fi

if changed "problem_first_ai/litellm/"; then
  gateway=problem_first_ai/litellm
  step "gateway scripts parse"
  for script in "$gateway/setup.sh" "$gateway/run_proxy.sh"; do
    bash -n "$script"
  done
  step "gateway Python lines are at most 120 characters"
  if awk 'length > 120 {print FILENAME ":" FNR; long = 1} END {exit !long}' \
      "$gateway"/validator/scripts/*.py "$gateway"/validator/tests/*.py "$gateway"/tests/*.py; then
    exit 1
  fi
  step "validator tests"
  uv run --frozen --project "$gateway" python -m unittest discover -s "$gateway/validator/tests" -q
  step "run_proxy.sh key handling and the pinned LiteLLM's .env loading"
  uv run --frozen --project "$gateway" python -m unittest discover -s "$gateway/tests" -q
fi

echo "All checks passed."
