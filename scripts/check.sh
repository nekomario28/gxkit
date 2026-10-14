#!/usr/bin/env bash
# The whole local gate, in one command — exactly what CI blocks on.
#
#   scripts/check.sh          # lint, format, types, tests, workflow lint, audit
#   scripts/check.sh --full   # also build the distributions and check them
#
# The first failing step stops the run with its exit code, so a red gate is
# unambiguous. This is the script to run before saying "it's green".
set -euo pipefail
cd "$(dirname "$0")/.."

FULL=0
[ "${1:-}" = "--full" ] && FULL=1

step() {
  printf '\n\033[1m==> %s\033[0m\n' "$*"
  "$@"
}

step python3 scripts/prepublish_check.py
step uv sync --all-packages --locked
step uv run ruff check packages scripts
step uv run ruff format --check packages scripts
step uvx --from shellcheck-py shellcheck scripts/*.sh
step uv run mypy packages/*/src
step uv run pytest \
  --cov=gxcore --cov=chartgx --cov=levelgx --cov=flowgx --cov=protogx \
  --cov=authzgx --cov=depsgx --cov=schemagx --cov=docgx --cov=shadergx \
  --cov=framegx --cov=gxkit --cov-fail-under=100
step uvx zizmor .
step uv run --with pip-audit pip-audit --skip-editable

if [ "$FULL" = 1 ]; then
  step rm -rf dist
  step uv build --all-packages -o dist
  step uvx twine check dist/*
fi

printf '\n\033[1;32mAll gates passed.\033[0m\n'
