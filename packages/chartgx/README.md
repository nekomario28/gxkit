# chartgx

**Inspect matplotlib charts for misleading or broken rendering.** A chart is a
claim about data; a truncated axis turns 8% into 300%. `chartgx inspect` reads
the figure's artist tree, reports each problem with a stable code and an exit
code, and writes a storyboard image with the problems outlined.

One of the [`gxkit`](../../README.md) tools, built on [`gxcore`](../gxcore).

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/chartgx" chartgx inspect chart.py
# local:  uvx --from ../../packages/chartgx chartgx inspect chart.py
```

## The contract

```
$ chartgx inspect bad_chart.py
bad_chart.py: Revenue by quarter
figure: 1 figure, 2 axes
storyboard: Revenue_by_quarter.storyboard.png
  ax[0]  bar   x=Quarter  y=—           1 series
  ax[1]  line  x=—        y=Growth (%)  1 series
inspect: 8 problems (2 errors)
  [1] error ax[0]  truncated-baseline: bar lengths start at y=40, not 0 — ...
  [2] error ax[0]  clipped-text: title '…' is cut off at the figure edge
  ...
```

- **Exit code 1** when any `error`-severity problem is found.
- `--json` prints the same report machine-readably; `--no-storyboard` skips the
  image; `-o name.png` names it.
- Severities: `error` (wrong or misleading) > `warn` (broken or hard to read) >
  `info` (a reviewer's note).

## Writing a chart

Any Python file that builds a figure — define `fig`, a `build()` returning one,
or just call `plt.figure()`:

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
ax.bar(["Q1", "Q2", "Q3"], [42, 51, 47])
ax.set_ylim(0, 60)  # the value axis starts at zero
ax.set_title("Revenue by quarter")
ax.set_xlabel("Quarter")
ax.set_ylabel("Revenue (£m)")
fig.tight_layout()
```

## Checks

| code | severity | what it means |
| --- | --- | --- |
| `truncated-baseline` | error | bars do not start at zero; lengths no longer show amounts |
| `clipped-text` | error | text is cut off at the figure edge |
| `text-overlap` | error | two texts cover each other |
| `log-nonpositive` | error | a value ≤ 0 on a log axis (the point vanishes) |
| `empty-chart` | error | no data is drawn |
| `no-title` / `no-xlabel` / `no-ylabel` | warn | missing context |
| `dual-axis` | warn | two y-scales invite false correlation |
| `too-many-series` | warn | more series than distinguishable colors |
| `pie-slices` | warn | a pie with more than six slices |
| `constant-series` | warn | a series that never changes |
| `clipped-data` | warn | data runs past the axis limits and is cut off |
| `legend-covers` | warn | the legend hides the data |
| `inverted-axis` | warn | a value axis that grows the wrong way |
| `small-text` | info | text below the readable floor |
| `no-units` | info | a value axis with no unit |
| `cut-value-axis` | info | a line axis cut away from zero (fine for trends) |

## Why it can be trusted

Every check is proven to fire on a chart with the defect and to stay quiet on
one without (`tests/`). An inspector that never fails is not an inspector.

MIT licensed.
