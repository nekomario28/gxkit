---
name: crongx
description: Use when an agent has written a schedule of timed runs (each with a start, a duration and a shared resource) and must check it before deploying — two runs holding the same resource at once, a duplicate run, a negative start or duration, or a run that never runs. Provides `crongx inspect` with stable codes, an exit code, `--json` and a storyboard. Part of the gxkit family.
---

# crongx

`crongx` reads a schedule written as data and reports where it collides before it
is deployed.

## Use it

```sh
uv tool install "git+https://github.com/nekomario28/gxkit#subdirectory=packages/crongx"
crongx inspect sched.py            # report + storyboard; exit 1 on any error
crongx inspect sched.py --json
crongx render  sched.py -o sched.png
```

Write the schedule as a Python file:

```python
import crongx as c

schedule = c.Schedule(
    runs=[
        c.Run("backup", start=0, duration=3600, resource="disk"),
        c.Run("reindex", start=3600, duration=1800, resource="disk"),
    ]
)
```

A run is `(name, start, duration, resource)` or a mapping with those keys. Or
module-level `RUNS` / `NAME`.

## What it catches

| code | severity | what it means |
| --- | --- | --- |
| `overlap` | error | two runs hold the same resource at once |
| `duplicate-run` | error | the same run name declared twice |
| `negative-start` | error | a run starts before zero |
| `negative-duration` | error | a run has a negative duration |
| `zero-duration` | info | a run has zero duration (it never runs) |
| `no-runs` | info | the schedule declares no runs |

## Why the checks can be trusted

Every check has a test that builds the defect and asserts it fires, and one that
asserts an honest schedule stays quiet (`packages/crongx/tests/`). The interval
overlap is cross-checked against `gxcore.geometry.overlap`.

## Where it fits

Part of `gxkit`; the `inspect` contract (stable codes, exit codes, `--json`, a
storyboard) is shared. See the family skill at the repository root.
