# gxcore

The shared review loop behind the [`gxkit`](../../README.md) tools.

`gxcore` owns everything that is identical across tools, so a new tool is only
a loader, a checks module, and a renderer:

- **`Problem` / `Report`** — severities, stable codes, located boxes.
- **Exit policy** — `error` fails the build; `warn` and `info` do not.
- **Storyboard** — draw numbered boxes over located problems (`gxcore.annotate`).
- **CLI** — `inspect` / `render`, `--json`, `--no-storyboard`, `-o`.
- **Testing helpers** — prove a check fires, and stays quiet.

```python
from gxcore import ERROR, Problem, Report, Tool, run
```

```python
TOOL = Tool(
    name="mytool",
    description="…",
    load=load,  # Path -> artifact
    inspect=inspect,  # artifact -> Report
    render=render,  # (artifact, Path|None, dpi|None) -> Path
    to_image=to_image,  # artifact -> PIL.Image, for the storyboard
)


def main(argv=None):
    return run(TOOL, argv)
```

## Inspection ownership

Routing and inspection share one module execution within an invocation; a later
invocation reads the current source. The loader must not reuse stale bytecode.

A baseline records occurrences, not a set of display locations. Checks that
report relationships supply stable identities independent of numeric prose and
layout order. Baseline format 2 rejects older records: recreate an accepted
baseline deliberately with `--write-baseline`, rather than guessing identities.

MIT licensed.
