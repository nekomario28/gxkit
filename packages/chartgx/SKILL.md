---
name: chartgx
description: Inspect matplotlib charts for misleading or broken rendering before shipping them — truncated bar baselines, clipped or overlapping text, missing titles/labels/units, dual axes, unreadable pies, constant or clipped data — with stable codes, exit codes, and an annotated storyboard. Use when a chart, graph, figure, plot, dashboard panel, or data visualization was produced by code (especially by an agent) and correctness matters: before publishing a chart, when a chart "looks off", or as the verification step after writing matplotlib. Not for interactive dashboards or for charts built with a non-matplotlib stack.
---

# chartgx — inspect charts before anyone trusts them

Part of the `gxkit` family; the review contract is shared with every `*gx` tool.

## Install

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/chartgx" chartgx --help
uv tool install ./packages/chartgx
```

## The loop

1. Write the chart as a Python file that builds a matplotlib figure.
2. `chartgx inspect chart.py` — prints the axes summary, each problem with a stable `code`, and writes `<name>.storyboard.png`. **Exit 1 on any error.**
3. Fix `error` and `warn` problems; inspect again. View the storyboard when you can — each numbered box proves a problem.
4. `chartgx render chart.py -o chart.png` for the final still.
5. `--json` gives the same report machine-readably.

## Severities

`error` = wrong or misleading (fail the build). `warn` = broken or hard to read.
`info` = a reviewer's note only.

## What it catches

| code | severity | fix |
| --- | --- | --- |
| `truncated-baseline` | error | `ax.set_ylim(bottom=0)` for bar charts |
| `clipped-text` | error | shorten the title / `fig.tight_layout()` |
| `text-overlap` | error | move or shorten labels |
| `log-nonpositive` | error | values ≤ 0 cannot go on a log axis |
| `empty-chart` | error | no data drawn — fix the data |
| `no-title`, `no-xlabel`, `no-ylabel` | warn | add them |
| `dual-axis` | warn | split into two charts |
| `too-many-series` | warn | facet or reduce series |
| `pie-slices` | warn | more than six slices: use bars |
| `constant-series` | warn | the data did not load / carries nothing |
| `clipped-data` | warn | widen the limits |
| `legend-covers` | warn | move the legend out of the data |
| `inverted-axis` | warn | orient the value axis the right way |
| `small-text` | info | raise font size |
| `no-units` | info | units on the value axis |
| `red-green` | info | a red/green encoding says nothing to a colour-blind reader |
| `cut-value-axis` | info | fine for trends, not for magnitudes |

Every check has a test that proves it fires on a chart with the defect and stays
quiet on one without (`tests/`).
