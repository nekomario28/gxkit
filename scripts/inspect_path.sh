#!/usr/bin/env bash
# Inspect every *.py artifact under a path, and fail closed when there is none.
#
# Extracted from the composite action so the logic is lintable (shellcheck) and
# testable (see packages/gxkit/tests/test_action_script.py) without running the
# action. Env:
#
#   TARGET  a file, or a directory to scan for *.py artifacts
#   TOOL    "" -> `gxkit inspect`;  a tool name -> `<tool> inspect`
#   FLAGS   extra flags, split on whitespace (e.g. "--json")
#
# Exit 0 only if every artifact is inspected and at least one was found.
set -uo pipefail

: "${TARGET:?TARGET is required}"

if [ -n "${TOOL:-}" ]; then
  cmd=("$TOOL" inspect)
else
  cmd=(gxkit inspect)
fi

if [ -d "$TARGET" ]; then
  # No `mapfile`: macOS ships bash 3.2, which does not have it.
  files=()
  while IFS= read -r f; do
    files+=("$f")
  done < <(find "$TARGET" -name '*.py' | sort)
  if [ "${#files[@]}" -eq 0 ]; then
    echo "::error::no *.py artifacts under $TARGET — refusing to report success"
    exit 1
  fi
elif [ -f "$TARGET" ]; then
  files=("$TARGET")
else
  echo "::error::path not found: $TARGET"
  exit 1
fi

rc=0
for f in "${files[@]}"; do
  echo "::group::${cmd[*]} $f"
  # shellcheck disable=SC2086  # FLAGS is intentionally word-split
  "${cmd[@]}" ${FLAGS:-} "$f" || rc=1
  echo "::endgroup::"
done
exit "$rc"
