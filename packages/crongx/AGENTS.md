# crongx, for AI agents

A person pointed you here. `crongx` checks that a schedule can run without
collision before it is deployed: declare each run with a start, a duration and the
resource it holds, then `crongx inspect` finds two runs that hold the same resource
at once, a duplicate run, a negative start or duration, and a run that never runs
— plus a storyboard.

This tool is part of `gxkit`; the review contract (`inspect`, `--json`, exit
codes, storyboard) is shared with every other tool in the family.

## Set it up

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/crongx" crongx --help
# or, from a clone:
uv tool install ./packages/crongx    # puts `crongx` on PATH
```

## The loop

1. **Write** the schedule as a `.py` file that builds a `Schedule` (or defines
   `RUNS` / `NAME`).
2. **Inspect** — `crongx inspect sched.py`. Prints the summary, every problem with
   a stable `code`, and writes `<name>.storyboard.png`.
   **Exit code 1 means at least one error.**
3. **Fix** and inspect again; look at the storyboard if you can view images.
4. **Render** — `crongx render sched.py -o sched.png`.

## Reading the report

- `error` — `overlap`, `duplicate-run`, `negative-start`, `negative-duration`.
- `info` — `zero-duration`, `no-runs`.

Common fixes: `overlap` → move one run or change its resource; `duplicate-run` →
merge them; `negative-start`/`negative-duration` → fix the number. Use `--json` to
branch on the result.
