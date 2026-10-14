# pipegx, for AI agents

A person pointed you here. `pipegx` checks that a build pipeline is runnable
before it runs: declare steps with their needs and produced artifacts, and the
goals the pipeline must deliver, then `pipegx inspect` finds a need that names no
step, a cycle, a step declared twice, an artifact produced twice, and a goal
nothing produces — plus a storyboard and the build order.

This tool is part of `gxkit`; the review contract (`inspect`, `--json`, exit
codes, storyboard) is shared with every other tool in the family.

## Set it up

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/pipegx" pipegx --help
# or, from a clone:
uv tool install ./packages/pipegx    # puts `pipegx` on PATH
```

## The loop

1. **Write** the pipeline as a `.py` file that builds a `Pipeline` (or defines
   `STEPS` / `GOALS` / `NAME`).
2. **Inspect** — `pipegx inspect pipe.py`. Prints the summary, the build order,
   every problem with a stable `code`, and writes `<name>.storyboard.png`.
   **Exit code 1 means at least one error.**
3. **Fix** and inspect again; look at the storyboard if you can view images.
4. **Render** — `pipegx render pipe.py -o pipe.png`.

## Reading the report

- `error` — `unknown-step`, `cycle`, `duplicate-step`, `duplicate-artifact`,
  `goal-not-produced`.
- `info` — `no-steps`, `no-goals`.

Common fixes: `unknown-step` → fix the name or add the step; `cycle` → break the
edge; `duplicate-artifact` → let one step own it; `goal-not-produced` → add a step
that produces it. Use `--json` to branch on the result.
