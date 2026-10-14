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
    out: list[tuple[str, Any]] = [("title", ax.title)]
    if _has_axis_labels(ax):
        out.append(("xlabel", ax.xaxis.label))
        out.append(("ylabel", ax.yaxis.label))
    out += [("text", t) for t in ax.texts]
    out += [("tick", t) for t in ax.get_xticklabels() + ax.get_yticklabels()]
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


def _check_units_note(ax: Any, i: int, kind: str, out: list[Problem]) -> None:
    from matplotlib.patches import Rectangle

    if kind == "pie":
        return
    axis, label = "y", ax.get_ylabel()
    if kind == "bar":
        rects = [p for p in ax.patches if isinstance(p, Rectangle)]
        if rects and rects[0].get_width() > rects[0].get_height():
            axis, label = "x", ax.get_xlabel()
    if label and not any(ch in label for ch in "([%£$€¥):"):
        out.append(
            Problem(
                INFO, "no-units", f"{axis}-axis label {label!r} names no unit", target=f"ax[{i}]"
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
    from matplotlib.patches import Rectangle

    if kind != "bar":
        return
    rects = [p for p in ax.patches if isinstance(p, Rectangle)]
    if not rects:
        return
    r = rects[0]
    vertical = r.get_height() >= r.get_width()
    lo, hi = ax.get_ylim() if vertical else ax.get_xlim()
    axis = "y" if vertical else "x"
    if not (lo <= 0 <= hi):
        out.append(
            Problem(
                ERROR,
                "truncated-baseline",
                f"bar lengths start at {axis}={lo:g}, not 0 — the bars no longer show amounts "
                "(the difference looks larger than it is). Draw the value axis from 0.",
                target=f"ax[{i}]",
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
    xlo, xhi = ax.get_xlim()
    ylo, yhi = ax.get_ylim()
    for j, ln in enumerate(ax.lines):
        try:
            xs = [float(v) for v in ln.get_xdata()]
            ys = [float(v) for v in ln.get_ydata()]
            if not xs:
                continue
            if min(xs) < xlo - 1e-9 or max(xs) > xhi + 1e-9:
                out.append(
                    Problem(
                        WARN,
                        "clipped-data",
                        f"line {j} runs past the x-limits and is cut off",
                        target=f"ax[{i}]",
                    )
                )
            if min(ys) < ylo - 1e-9 or max(ys) > yhi + 1e-9:
                out.append(
                    Problem(
                        WARN,
                        "clipped-data",
                        f"line {j} runs past the y-limits and is cut off",
                        target=f"ax[{i}]",
                    )
                )
        except Exception:
            continue


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
    out.extend(
        check_text_layout(
            _text_items(ax, renderer), _figure_box(fig), target=f"ax[{i}]", surface="figure"
        )
    )


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
    try:
        fn()
    except Exception:
        return
