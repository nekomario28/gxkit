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
| `red-green` | info | a red/green encoding says nothing to a colour-blind reader |
| `cut-value-axis` | info | a line axis cut away from zero (fine for trends) |

### Declared charts

A chart written as data — a figspec model, JSON — is checked without matplotlib
and without running anything:

```sh
chartgx inspect revenue.json
```

The codes are the same where the concept is the same, so a finding does not have
two names depending on which route produced it. Six can only come from a
declaration, because a figure cannot express them:

| code | severity | what it means |
| --- | --- | --- |
| `mismatched-lengths` | error | an error array, a bar group or a heatmap's rows and labels disagree in number with what they annotate |
| `non-finite-value` | error | a declared number is NaN or infinite and cannot be placed |
| `two-error-shapes` | error | a mark declares symmetric and asymmetric error bars at once |
| `negative-error` | error | an error magnitude is negative, which is not a distance |
| `short-line` | error | a line has fewer than two points, so there is no line to draw |
| `ambiguous-labels` | error | two marks name one axis differently, so one would caption the other's data |

The kinds are `line`, `scatter`, `bar`, `grouped_bar` and `heatmap`. A `heatmap`
carries a matrix (`values`), optional `row_labels`/`col_labels` and a `color_map`
from the model's closed set — an unknown ramp is an input failure naming the value,
not a silent fall back to the default. An **empty mark** (a scatter with no points,
a bar with no categories, a matrix with no cells) is `empty-chart`: nothing to draw
is an error, not a clean report.

A declaration has no storyboard *here*: box numbers are drawn over a figure's
artists, and a declaration has no artists, so the report is printed and the image is
skipped with that reason. The renderer that owns the model can draw one —
`figspec storyboard model.json -o model.storyboard.svg` boxes the marks these
findings name. An unknown key, a mark kind the model does not have, and a member
that cannot be read are input failures (exit 2) naming where they are wrong.

## Why it can be trusted

Every check is proven to fire on a chart with the defect and to stay quiet on
one without (`tests/`). An inspector that never fails is not an inspector.

MIT licensed.
