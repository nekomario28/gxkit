# Contributing

## Develop

```sh
uv sync --all-packages
scripts/check.sh          # the whole gate: lint, format, --strict types, tests, audit
```

`scripts/check.sh --full` also builds the distributions and runs `twine check`.
That script is what CI blocks on; a green local run is the prerequisite for a
PR.

## Add a tool

Read [`docs/BUILDING.md`](docs/BUILDING.md) (and the `agent-native-inspect-tools`
skill). A tool is a loader, a checks module and a renderer; its `tool.py` is five
lines.

## Before opening a PR

- Every new check has a test that proves it fires on a defective artifact **and**
  stays quiet on an honest one.
- New problem codes are added to `packages/gxkit/src/gxkit/codes.py` — a test
  enforces this.
- The tool ships `README.md`, `AGENTS.md`, `llms.txt`, `SKILL.md` and `LICENSE`.
- `scripts/check.sh` is green.
- A fixed defect ships with a guard that fails on the old state (see the
  `mistake-to-guard` skill).
