# chartgx, for AI agents

A person pointed you here. `chartgx` checks that a chart is correct and honest
before anyone trusts it: write a matplotlib figure as a Python file, then
`chartgx inspect` reports what is wrong and draws a storyboard with the evidence.

This tool is part of `gxkit`; the review contract (`inspect`, `--json`, exit
codes, storyboard) is shared with every other tool in the family.

## Set it up

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/chartgx" chartgx --help
# or, from a clone:
uv tool install ./packages/chartgx    # puts `chartgx` on PATH
```

## The loop

1. **Write** the chart as a `.py` file that builds a matplotlib figure.
2. **Inspect** — `chartgx inspect chart.py`. Prints the axes summary, every
   problem with a stable `code`, and writes `<name>.storyboard.png`.
   **Exit code 1 means at least one error.**
3. **Fix** the `error` and `warn` problems, inspect again. Look at the
   storyboard if you can view images — each numbered box proves a problem.
4. **Render** — `chartgx render chart.py -o chart.png`.

## Reading the report

- `error` — the chart is wrong or misleading. Fix it. Exit code 1.
- `warn` — broken or hard to read. Fix it.
- `info` — a note; safe to leave when the choice is deliberate.

Common fixes: `truncated-baseline` → `ax.set_ylim(bottom=0)`; `clipped-text` →
shorten the title or `fig.tight_layout()`; `no-ylabel` → `ax.set_ylabel(...)`;
`dual-axis` → drop the second axis and split the chart; `text-overlap` → move or
shorten the labels. Use `--json` to branch on the result.
