---
name: pipegx
description: Use when an agent has written a build pipeline (steps with needs and produced artifacts, plus goals) and must check it before running — a need that names no step, a cycle, a duplicate step or artifact, or a goal nothing produces. Provides `pipegx inspect` with stable codes, an exit code, `--json`, the build order and a storyboard. Part of the gxkit family.
---

# pipegx

`pipegx` reads a build pipeline written as data and reports what is wrong before it
runs — and prints the build order when the graph is a DAG.

## Use it

```sh
uv tool install "git+https://github.com/nekomario28/gxkit#subdirectory=packages/pipegx"
pipegx inspect pipe.py            # report + build order + storyboard; exit 1 on any error
pipegx inspect pipe.py --json
pipegx render  pipe.py -o pipe.png
```

Write the pipeline as a Python file:

```python
import pipegx as p

pipeline = p.Pipeline(
    steps=[
        p.Step("build", produces=["app"]),
        p.Step("package", needs=["build"], produces=["app.tar"]),
    ],
    goals=["app.tar"],
)
```

Or module-level `STEPS` / `GOALS` / `NAME`.

## What it catches

| code | severity | what it means |
| --- | --- | --- |
| `unknown-step` | error | a `needs` names a step that does not exist |
| `cycle` | error | the needs graph has a cycle; one finding per cyclic component |
| `duplicate-step` | error | a step declared twice |
| `duplicate-artifact` | error | two steps produce the same artifact |
| `goal-not-produced` | error | a goal no step produces |
| `no-steps` | info | the pipeline declares no steps |
| `no-goals` | info | the pipeline declares no goals |

## Why the checks can be trusted

Every check has a test that builds the defect and asserts it fires, and one that
asserts an honest pipeline stays quiet (`packages/pipegx/tests/`). Cycles and the
build order come from `gxcore.graph`.

## Where it fits

Part of `gxkit`; the `inspect` contract (stable codes, exit codes, `--json`, a
storyboard) is shared. See the family skill at the repository root.
