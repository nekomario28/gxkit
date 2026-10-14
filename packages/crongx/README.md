# crongx

**Inspect a schedule of timed runs for collisions.** Declare each run with a
start, a duration and the resource it holds; `crongx inspect` finds two runs that
hold the same resource at once, a duplicate run, a negative start or duration,
and a run that never runs.

One of the [`gxkit`](../../README.md) tools, built on [`gxcore`](../gxcore).

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/crongx" crongx inspect sched.py
# local:  uvx --from ../../packages/crongx crongx inspect sched.py
```

## Writing a schedule

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

## The contract

```
$ crongx inspect broken_schedule.py
broken_schedule.py: Nightly
schedule: 5 runs
storyboard: Nightly.storyboard.png
  5 runs
inspect: 4 problems (4 errors)
  [1] error r[1]      overlap: 'backup' and 'reindex' both hold 'disk' at once
  [2] error r[2]      duplicate-run: run 'backup' is declared more than once
  [3] error r[3]      negative-start: 'purge' starts at -60, before zero
  [4] error r[4]      negative-duration: 'probe' has a duration of -5
```

- **Exit code 1** when any `error`-severity problem is found.
- `--json` prints the same report machine-readably; `--no-storyboard` skips the
  image; `-o name.png` names it.

## Checks

| code | severity | what it means |
| --- | --- | --- |
| `overlap` | error | two runs hold the same resource at once |
| `duplicate-run` | error | the same run name declared twice |
| `negative-start` | error | a run starts before zero |
| `negative-duration` | error | a run has a negative duration |
| `zero-duration` | info | a run has zero duration (it never runs) |
| `no-runs` | info | the schedule declares no runs |

## Why it can be trusted

Every check is proven to fire on a schedule with the fault and to stay quiet on
one without (`tests/`); the interval overlap is cross-checked against the shared
box-overlap definition on random runs.

MIT licensed.
