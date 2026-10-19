"""chartgx's domain knowledge: what makes a chart wrong or hard to read.

Each check reads the figure's own artist tree and appends `gxcore.Problem`s.
Everything mechanical — severities, storyboards, CLI, JSON — is `gxcore`'s.
"""

from __future__ import annotations

import contextlib
from typing import Any

from gxcore import ERROR, INFO, WARN, Problem, Report
from gxcore.geometry import area, overlap
from gxcore.layout import TextBox
from gxcore.layout import check as check_text_layout

from .loader import load_figure  # noqa: F401  (re-exported for callers)

# --------------------------------------------------------------------------- #
# artist inspection helpers
# --------------------------------------------------------------------------- #


def _renderer(fig: Any) -> Any:
    fig.canvas.draw()
    return fig.canvas.get_renderer()


def _bbox(text: Any, renderer: Any) -> tuple[float, float, float, float] | None:
    try:
        if not text.get_text().strip() or not text.get_visible():
            return None
        b = text.get_window_extent(renderer)
        return (b.x0, b.y0, b.x1, b.y1)
    except Exception:
        return None


def _figure_box(fig: Any) -> tuple[float, float, float, float]:
    return (fig.bbox.x0, fig.bbox.y0, fig.bbox.x1, fig.bbox.y1)


def _has_axis_labels(ax: Any) -> bool:
    from matplotlib.patches import Wedge

    return not any(isinstance(p, Wedge) for p in ax.patches)


def _texts(ax: Any) -> list[tuple[str, Any]]:
    if not ax.get_visible():
        return []
    out: list[tuple[str, Any]] = [("title", ax.title)]
    # Axes3D draws its own axes with _axis3don, ignoring 2D's axison and each
    # Axis.get_visible(). Keep the projection's drawing policy, not a 2D proxy.
    axis3d_on = getattr(ax, "_axis3don", None)
    axes = [
        axis
        for axis in (ax.xaxis, ax.yaxis)
        if (axis3d_on if axis3d_on is not None else ax.axison and axis.get_visible())
    ]
    if _has_axis_labels(ax):
        out += [(axis.axis_name + "label", axis.label) for axis in axes]
    out += [("text", t) for t in ax.texts]
    for axis in axes:
        # Axis.draw uses this same selector: a visible label can belong to an
        # off-view tick that is never drawn. Reuse Matplotlib's transformed-range
        # and boundary-tolerance policy, including minor ticks and inverted axes.
        for tick in axis._update_ticks():
            if tick.get_visible():
                out += [("tick", tick.label1), ("tick", tick.label2)]
    legend = ax.get_legend()
    if legend is not None:
        out += [("legend", t) for t in legend.get_texts()]
    return out


def _classify(ax: Any) -> str:
    from matplotlib.collections import PathCollection, PolyCollection
    from matplotlib.patches import Rectangle, Wedge

    if any(isinstance(p, Wedge) for p in ax.patches):
        return "pie"
    if any(isinstance(p, Rectangle) for p in ax.patches):
        return "bar"
    for c in ax.collections:
        if isinstance(c, PathCollection):
            return "scatter"
        if isinstance(c, PolyCollection):
            return "area"
    if ax.lines:
        return "line"
    if ax.images:
        return "image"
    if ax.collections:
        return "collection"
    return "empty"


def _series_count(ax: Any, kind: str) -> int:
    if kind == "bar":
        try:
            return max(1, len(ax.containers))
        except Exception:
            return 1
    if kind == "pie":
        return len(ax.patches)
    if kind in ("line", "area"):
        return len(ax.lines)
    if kind == "scatter":
        from matplotlib.collections import PathCollection

        return len([c for c in ax.collections if isinstance(c, PathCollection)])
    return len(ax.lines) + len(ax.collections)


def _series_colors(ax: Any) -> list[str]:
    colors: list[str] = []
    for ln in ax.lines:
        with contextlib.suppress(Exception):
            colors.append(str(ln.get_color()))
    for c in ax.collections:
        with contextlib.suppress(Exception):
            fc = c.get_facecolor()
            if len(fc):
                colors.append(str(fc[0]))
    return colors


def _data_bbox(ax: Any, renderer: Any) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []
    for artist in list(ax.lines) + list(ax.collections):
        try:
            b = artist.get_window_extent(renderer)
            xs += [b.x0, b.x1]
            ys += [b.y0, b.y1]
        except Exception:
            continue
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def _twins(ax: Any) -> list[Any]:
    try:
        return [s for s in ax._twinned_axes.get_siblings(ax) if s is not ax]
    except Exception:
        return []


def _shared_x_has_label(ax: Any) -> bool:
    try:
        for sib in ax.get_shared_x_axes().get_siblings(ax):
            if sib is not ax and sib.get_xlabel().strip():
                return True
    except Exception:
        pass
    return False


def _hex_to_rgb(c: str) -> tuple[int, int, int] | None:
    c = c.strip()
    if c.startswith("#") and len(c) >= 7:
        try:
            return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
        except ValueError:
            return None
    return None


def _is_red(c: str) -> bool:
    rgb = _hex_to_rgb(c)
    if rgb is None:
        return False
    r, g, b = rgb
    return r > 120 and g < 90 and b < 90


def _is_green(c: str) -> bool:
    rgb = _hex_to_rgb(c)
    if rgb is None:
        return False
    r, g, b = rgb
    return g > 100 and r < 110 and b < 110


# --------------------------------------------------------------------------- #
# checks
# --------------------------------------------------------------------------- #


def _check_empty(ax: Any, i: int, kind: str, out: list[Problem]) -> bool:
    if kind == "empty":
        out.append(
            Problem(ERROR, "empty-chart", "no data is drawn on this axes", target=f"ax[{i}]")
        )
        return True
    return False


def _bar_value_axes(ax: Any) -> list[str]:
    from matplotlib.container import BarContainer

    # Width and height have different units. A small amount or negative value
    # cannot tell us which dimension is categorical; bar/barh already declare it.
    axes: list[str] = []
    for container in getattr(ax, "containers", ()):
        if isinstance(container, BarContainer):
            axis = {"vertical": "y", "horizontal": "x"}.get(container.orientation or "")
            if axis is not None and axis not in axes:
                axes.append(axis)
    return axes


def _check_units_note(ax: Any, i: int, kind: str, out: list[Problem]) -> None:
    if kind == "pie":
        return
    for axis in _bar_value_axes(ax) if kind == "bar" else ["y"]:
        label = ax.get_ylabel() if axis == "y" else ax.get_xlabel()
        if label and not any(ch in label for ch in "([%£$€¥):"):
            out.append(
                Problem(
                    INFO,
                    "no-units",
                    f"{axis}-axis label {label!r} names no unit",
                    target=f"ax[{i}]",
                )
            )


def _check_title(fig: Any, axes_list: list[Any], out: list[Problem]) -> None:
    if fig.get_suptitle().strip() or any(a.get_title().strip() for a in axes_list):
        return
    out.append(Problem(WARN, "no-title", "the figure has no title or suptitle"))


def _check_axis_labels(ax: Any, i: int, kind: str, skip_x: bool, out: list[Problem]) -> None:
    if kind == "pie":
        return
    if not skip_x and not ax.get_xlabel().strip() and not _shared_x_has_label(ax):
        out.append(Problem(WARN, "no-xlabel", "x-axis has no label", target=f"ax[{i}]"))
    if not ax.get_ylabel().strip():
        out.append(Problem(WARN, "no-ylabel", "y-axis has no label", target=f"ax[{i}]"))


def _check_bar_baseline(ax: Any, i: int, kind: str, out: list[Problem]) -> None:
    if kind != "bar":
        return
    for axis in _bar_value_axes(ax):
        lo, hi = sorted(ax.get_ylim() if axis == "y" else ax.get_xlim())
        if not (lo <= 0 <= hi):
            edge = lo if lo > 0 else hi
            out.append(
                Problem(
                    ERROR,
                    "truncated-baseline",
                    f"bar lengths start at {axis}={edge:g}, not 0 — the bars no longer show amounts "
                    "(the difference looks larger than it is). Draw the value axis from 0.",
                    target=f"ax[{i}]",
                    identity=(axis,),
                )
            )


def _check_line_baseline(ax: Any, i: int, kind: str, out: list[Problem]) -> None:
    if kind not in ("line", "area", "scatter", "collection"):
        return
    ylo = ax.get_ylim()[0]
    if ylo > 0:
        out.append(
            Problem(
                INFO,
                "cut-value-axis",
                f"the {kind} axis is cut at y={ylo:g}: fine for change over time, but not for "
                "comparing magnitudes.",
                target=f"ax[{i}]",
            )
        )


def _check_constant(ax: Any, i: int, out: list[Problem]) -> None:
    for j, ln in enumerate(ax.lines):
        try:
            ys = ln.get_ydata()
            if len(ys) > 2 and float(min(ys)) == float(max(ys)):
                out.append(
                    Problem(
                        WARN,
                        "constant-series",
                        f"series {j} is constant ({float(ys[0]):g}) — it carries no information "
                        "or the data did not load.",
                        target=f"ax[{i}]",
                    )
                )
        except Exception:
            continue


def _check_clipped_data(ax: Any, i: int, out: list[Problem]) -> None:
    import numpy as np
    from matplotlib.collections import PathCollection

    limits = (ax.get_xlim(), ax.get_ylim())
    sources = (("line", ax.lines), ("scatter", getattr(ax, "collections", ())))
    for kind, artists in sources:
        for j, artist in enumerate(artists):
            if kind == "scatter" and not isinstance(artist, PathCollection):
                continue
            try:
                if not artist.get_clip_on():
                    continue
                transform = (
                    artist.get_transform() if kind == "line" else artist.get_offset_transform()
                )
                # The historical spelling is a permanent Matplotlib alias, also
                # present in older supported versions. Reference lines use data
                # on one axis and axes-relative positions on the other.
                data_axes = transform.contains_branch_seperately(ax.transData)
                points = artist.get_xydata() if kind == "line" else artist.get_offsets()
                points = np.ma.asarray(points, dtype=float).filled(np.nan)
                points = (transform - ax.transData).transform(points)
                # A point with either coordinate masked/nonfinite is not drawn.
                points = points[np.isfinite(points).all(axis=1)]
            except Exception:
                continue
            for column, (axis, bounds) in enumerate(zip(("x", "y"), limits, strict=True)):
                values = points[:, column]
                lo, hi = sorted(bounds)
                if (
                    data_axes[column]
                    and values.size
                    and (values.min() < lo - 1e-9 or values.max() > hi + 1e-9)
                ):
                    out.append(
                        Problem(
                            WARN,
                            "clipped-data",
                            f"{kind} {j} runs past the {axis}-limits and is cut off",
                            target=f"ax[{i}]",
                        )
                    )


def _check_log(ax: Any, i: int, out: list[Problem]) -> None:
    if ax.get_yscale() == "log":
        for j, ln in enumerate(ax.lines):
            try:
                if min(float(v) for v in ln.get_ydata()) <= 0:
                    out.append(
                        Problem(
                            ERROR,
                            "log-nonpositive",
                            f"line {j} has a value <= 0 on a log y-axis — those points vanish",
                            target=f"ax[{i}]",
                        )
                    )
            except Exception:
                continue
    if ax.get_xscale() == "log":
        for j, ln in enumerate(ax.lines):
            try:
                if min(float(v) for v in ln.get_xdata()) <= 0:
                    out.append(
                        Problem(
                            ERROR,
                            "log-nonpositive",
                            f"line {j} has a value <= 0 on a log x-axis — those points vanish",
                            target=f"ax[{i}]",
                        )
                    )
            except Exception:
                continue
    # Bars are patches, not lines, so a bar of 0 on a log axis was reported clean by
    # the figure route while the declared route reports `log-nonpositive` — the same
    # concept and the same code name, disagreeing on the same chart.
    if ax.get_yscale() == "log":
        # Every patch answers `get_height` (a `Circle` and an annotation too, measured),
        # so there is no guard here: a try/except would be a line nothing can reach.
        for j, patch in enumerate(ax.patches):
            if float(patch.get_height()) <= 0:
                out.append(
                    Problem(
                        ERROR,
                        "log-nonpositive",
                        f"bar {j} has a height <= 0 on a log y-axis — it vanishes",
                        target=f"ax[{i}]",
                    )
                )


def _check_inverted_axis(ax: Any, i: int, out: list[Problem]) -> None:
    for axis, limits in (("y", ax.get_ylim()), ("x", ax.get_xlim())):
        if limits[0] > limits[1]:
            out.append(
                Problem(
                    WARN,
                    "inverted-axis",
                    f"the {axis}-axis is inverted ({limits[0]:g} at the near edge, "
                    f"{limits[1]:g} at the far edge) — values grow the wrong way",
                    target=f"ax[{i}]",
                )
            )


def _check_dual_axis(ax: Any, i: int, primary: bool, out: list[Problem]) -> None:
    if _twins(ax) and primary:
        out.append(
            Problem(
                WARN,
                "dual-axis",
                "a second y-axis shares this plot — two scales invite false correlation",
                target=f"ax[{i}]",
            )
        )


def _check_series_colors(ax: Any, i: int, kind: str, out: list[Problem]) -> None:
    n = _series_count(ax, kind)
    if n > 10:
        out.append(
            Problem(
                WARN,
                "too-many-series",
                f"{n} series share the default color cycle — they repeat and are "
                "hard to tell apart",
                target=f"ax[{i}]",
            )
        )
    look = {c.lower() for c in _series_colors(ax)}
    if any(_is_red(c) for c in look) and any(_is_green(c) for c in look) and len(look) <= 4:
        out.append(
            Problem(
                INFO,
                "red-green",
                "the series are told apart by red/green alone — hard for "
                "color-vision-deficient readers; add line styles or markers",
                target=f"ax[{i}]",
            )
        )


def _check_pie(ax: Any, i: int, kind: str, out: list[Problem]) -> None:
    if kind != "pie":
        return
    from matplotlib.patches import Wedge

    n = len([p for p in ax.patches if isinstance(p, Wedge)])
    if n > 6:
        out.append(
            Problem(
                WARN,
                "pie-slices",
                f"a pie with {n} slices is hard to read — use a bar chart or group "
                "the small slices",
                target=f"ax[{i}]",
            )
        )


def _text_items(ax: Any, renderer: Any) -> list[TextBox]:
    items: list[TextBox] = []
    for role, t in _texts(ax):
        b = _bbox(t, renderer)
        if b is None:
            continue
        try:
            size = float(t.get_fontsize())
        except Exception:
            size = None
        items.append(TextBox(role, t.get_text(), b, size))
    return items


def _check_text(fig: Any, ax: Any, i: int, renderer: Any, out: list[Problem]) -> None:
    problems = check_text_layout(
        _text_items(ax, renderer), _figure_box(fig), target=f"ax[{i}]", surface="figure"
    )
    for problem in problems:
        if problem.code == "clipped-text":
            problem.message += (
                "; wrap the text or reduce its fontsize/adjust figure margins; for a title, "
                "shorten it or insert '\\n' in ax.set_title(...). Preserve data values and "
                "axis limits; changing them is not a text-layout repair. Redraw and inspect again"
            )
    out.extend(problems)


def _check_legend_covers(ax: Any, i: int, renderer: Any, out: list[Problem]) -> None:
    leg = ax.get_legend()
    if leg is None:
        return
    try:
        lb = leg.get_window_extent(renderer)
        lbb = (lb.x0, lb.y0, lb.x1, lb.y1)
    except Exception:
        return
    db = _data_bbox(ax, renderer)
    if db is None:
        return
    if overlap(lbb, db) > 0.15 * area(lbb):
        out.append(
            Problem(
                WARN,
                "legend-covers",
                "the legend sits over the plotted data",
                target=f"ax[{i}]",
                bbox=lbb,
            )
        )


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #


def _axes_line(ax: Any, i: int) -> str:
    kind = _classify(ax)
    x = ax.get_xlabel() or "—"
    y = ax.get_ylabel() or "—"
    return f"ax[{i}]  {kind:<9} x={x}  y={y}  {_series_count(ax, kind)} series"


_STRUCTURAL = {"truncated-baseline", "empty-chart", "dual-axis"}


def _locate_structural(report: Report, axes_list: list[Any], renderer: Any) -> None:
    if renderer is None:
        return
    seen: set[str] = set()
    for p in report.sorted():
        if p.bbox is not None or not p.target or p.code not in _STRUCTURAL:
            continue
        if p.target in seen:
            continue
        try:
            b = axes_list[int(p.target[3:-1])].get_window_extent(renderer)
            p.bbox = (b.x0, b.y0, b.x1, b.y1)
            seen.add(p.target)
        except Exception:
            continue


def inspect_figure(fig: Any, name: str = "figure") -> Report:
    axes_list = list(fig.axes)
    report = Report(
        name=name,
        subject=f"figure: 1 figure, {len(axes_list)} axes",
        details=[_axes_line(ax, i) for i, ax in enumerate(axes_list)],
    )

    try:
        renderer = _renderer(fig)
    except Exception:
        renderer = None

    out: list[Problem] = []
    _guard(_check_title, fig, axes_list, out)

    for i, ax in enumerate(axes_list):
        kind = _classify(ax)
        if _check_empty(ax, i, kind, out):
            continue
        secondary = any((s in axes_list) and axes_list.index(s) < i for s in _twins(ax))
        _guard(_check_axis_labels, ax, i, kind, secondary, out)
        _guard(_check_units_note, ax, i, kind, out)
        _guard(_check_bar_baseline, ax, i, kind, out)
        _guard(_check_line_baseline, ax, i, kind, out)
        _guard(_check_constant, ax, i, out)
        _guard(_check_clipped_data, ax, i, out)
        _guard(_check_log, ax, i, out)
        _guard(_check_inverted_axis, ax, i, out)
        _guard(_check_dual_axis, ax, i, not secondary, out)
        _guard(_check_series_colors, ax, i, kind, out)
        _guard(_check_pie, ax, i, kind, out)
        if renderer is not None:
            _guard(_check_text, fig, ax, i, renderer, out)
            _guard(_check_legend_covers, ax, i, renderer, out)

    report.problems = out
    _locate_structural(report, axes_list, renderer)
    return report


def _guard(fn: Any, *args: Any) -> None:
    """Run one check; a check that throws must never hide the others."""
    try:
        fn(*args)
    except Exception:
        return
