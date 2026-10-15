# pipegx

**Inspect a build pipeline DAG before you run it.** Declare steps with their needs
and the artifacts they produce, and the goals the pipeline must deliver;
`pipegx inspect` finds a need that names no step, a cycle, a step declared twice,
an artifact produced twice, and a goal nothing produces.

One of the [`gxkit`](../../README.md) tools, built on [`gxcore`](../gxcore)
(using its cycle detection and topological sort).

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/pipegx" pipegx inspect pipe.py
# local:  uvx --from ../../packages/pipegx pipegx inspect pipe.py
```

## Writing a pipeline

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

Names are names: `goals` must be a list of strings. A malformed member or
collection rejects the artifact with its field and index (exit 2) instead of
disappearing, and a recognized declaration is never replaced by another one.

## The contract

```
$ pipegx inspect broken_pipeline.py
broken_pipeline.py: Build
pipeline: 5 steps, 3 artifacts
storyboard: Build.storyboard.png
  5 steps, 3 artifacts
  goals: missing.tar
inspect: 5 problems (5 errors)
  [1] error -          goal-not-produced: the goal 'missing.tar' is produced by no step
  [2] error deploy     cycle: the needs graph has a cycle: deploy → package → deploy
  [3] error test       unknown-step: 'test' needs 'ghost', which is not a step
  [4] error test       duplicate-artifact: 'app' is produced by both 'build' and 'test'
  [5] error test       duplicate-step: step 'test' is declared more than once
```

- **Exit code 1** when any `error`-severity problem is found.
- `--json` prints the same report machine-readably; `--no-storyboard` skips the
  image; `-o name.png` names it.

## Checks

| code | severity | what it means |
| --- | --- | --- |
| `unknown-step` | error | a `needs` names a step that does not exist |
| `cycle` | error | the needs graph has a cycle; one finding per cyclic component |
| `duplicate-step` | error | a step declared twice |
| `duplicate-artifact` | error | two steps produce the same artifact |
| `goal-not-produced` | error | a goal no step produces; one finding per goal |
| `no-steps` | info | the pipeline declares no steps |
| `no-goals` | info | the pipeline declares no goals |

## Why it can be trusted

Every check is proven to fire on a pipeline with the fault and to stay quiet on
one without (`tests/`). Cycles and the build order come from `gxcore.graph`.

MIT licensed.
