# Contributing

## Develop

```sh
uv sync --all-packages
uv run pytest
uvx ruff check packages scripts --select F,E9,B
python scripts/prepublish_check.py
```

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
- `uv run pytest`, ruff and `scripts/prepublish_check.py` are green.
