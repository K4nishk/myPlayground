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

if changed "problem_first_ai/litellm/"; then
  gateway=problem_first_ai/litellm
  step "gateway scripts parse"
  for script in "$gateway/setup.sh" "$gateway/run_proxy.sh"; do
    bash -n "$script"
  done
  step "validator lines are at most 120 characters"
  if awk 'length > 120 {print FILENAME ":" FNR; long = 1} END {exit !long}' \
      "$gateway"/validator/scripts/*.py "$gateway"/validator/tests/*.py; then
    exit 1
  fi
  step "validator tests"
  uv run --frozen --project "$gateway" python -m unittest discover -s "$gateway/validator/tests" -q
fi

echo "All checks passed."
