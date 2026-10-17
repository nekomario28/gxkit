"""Inspect a chart declared as data, without matplotlib and without executing it.

A chart written as a figspec model (JSON: marks, axes, labels) is checked here
directly. Nothing is imported and nothing runs, so this route works where
matplotlib is unavailable and where running the artifact's code is unwanted — in
a sandbox, in a review of someone else's file, or in a gate on a declaration a
model produced.

The rules are this tool's own, with this tool's codes and severities: a model is a
different artifact from a figure, so what can be said about it is a smaller,
sharper set. `figspec` implements the same rules for the model it defines; neither
project depends on the other, and that is deliberate — gxkit's contract has to
stand on its own.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, cast

from gxcore import ERROR, WARN, Problem, Report
from gxcore.loading import InvalidArtifact

#: Every code this route can report, with its severity. This literal table is what
#: the codebook guard reads, so the contract cannot drift from the source.
#:
#: The codes are chartgx's existing ones wherever the concept is the same
#: (`empty-chart`, `truncated-baseline`, `no-title`, `log-nonpositive`,
#: `no-xlabel`/`no-ylabel`, `mismatched-lengths`, ...), because a user who has seen
#: a finding from the figure route must not have to learn a second name for it
#: here. Only what the model can express and a figure cannot is new.
MODEL_CODES: dict[str, str] = {
    "empty-chart": ERROR,
    "short-line": ERROR,
    "ambiguous-labels": ERROR,
    "truncated-baseline": ERROR,
    "log-nonpositive": ERROR,
    "inapplicable-axis-setting": ERROR,
    "mismatched-lengths": ERROR,
    "non-finite-value": ERROR,
    "two-error-shapes": ERROR,
    "negative-error": ERROR,
    "no-title": WARN,
    "no-xlabel": WARN,
    "no-ylabel": WARN,
}

MARK_KINDS = ("line", "scatter", "bar", "grouped_bar", "heatmap")

#: The fields each kind may carry. An unknown field is refused rather than
#: ignored: a mistyped optional field (`colr` for `color`) would otherwise leave
#: the drawing to the default and report a clean figure.
MARK_FIELDS: dict[str, frozenset[str]] = {
    "line": frozenset({"kind", "points", "y_err", "y_err_asymmetric", "color", "label"}),
    "scatter": frozenset({"kind", "points", "y_err", "y_err_asymmetric", "size", "color", "label"}),
    "bar": frozenset({"kind", "categories", "values", "color", "label"}),
    "grouped_bar": frozenset({"kind", "categories", "series"}),
    "heatmap": frozenset({"kind", "values", "row_labels", "col_labels", "color_map", "label"}),
}

#: The axis scales the model names.
SCALES = frozenset({"linear", "log"})

#: The fields one series of a grouped bar may carry.
SERIES_FIELDS = frozenset({"values", "label", "color"})

#: The colour ramps the model names, matching the declaration this tool reads.
COLOR_MAPS = frozenset(
    {"viridis", "turbo", "inferno", "magma", "plasma", "cividis", "warm", "cool", "cubehelix"}
)
FIGURE_FIELDS = {
    "marks",
    "title",
    "x_label",
    "y_label",
    "x_scale",
    "y_scale",
    "y_min",
    "width",
    "height",
}


class InvalidModel(InvalidArtifact):
    """The file is a recognized chart declaration that cannot be read.

    `gxcore.loading.InvalidArtifact` is the family's marker for exactly this: a
    shape the tool recognizes, with a member it cannot read. Subclassing it keeps
    the loader's guarantee — a recognized malformed declaration is refused, never
    handed to another representation's fallback — for this route too.
    """


def load_model(path: str | Path) -> dict[str, Any]:
    """Read a figspec model, refusing anything the format does not name."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise InvalidModel(f"{path}: {error}") from error
    try:
        model = json.loads(text)
    except json.JSONDecodeError as error:
        raise InvalidModel(f"{path}: not JSON ({error})") from error
    model = _expect_object(model, f"{path}")
    unknown = sorted(key for key in model if key not in FIGURE_FIELDS)
    if unknown:
        raise InvalidModel(f"{path}: unrecognised key(s) {unknown}")
    for optional in ("width", "height"):
        if optional in model:
            value = model[optional]
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise InvalidModel(f"{path}: {optional} is {value!r}, expected a positive integer")
    for scale_field in ("x_scale", "y_scale"):
        if scale_field in model and model[scale_field] not in SCALES:
            # A typo'd `logarithmic` used to fall back to the linear default, which
            # silently disabled every log-axis check for the figure and made this
            # route disagree with the renderer that owns the model.
            raise InvalidModel(
                f"{path}: {scale_field} is {model[scale_field]!r}, expected one of {sorted(SCALES)}"
            )
    marks = model.get("marks")
    if not isinstance(marks, list):
        raise InvalidModel(f"{path}: 'marks' must be a list")
    for index, mark in enumerate(marks):
        _expect_object(mark, f"{path}: marks[{index}]")
        kind = mark.get("kind")
        if kind not in MARK_KINDS:
            raise InvalidModel(
                f"{path}: marks[{index}].kind is {kind!r}, expected one of {list(MARK_KINDS)}"
            )
        unknown = sorted(key for key in mark if key not in MARK_FIELDS[str(kind)])
        if unknown:
            raise InvalidModel(
                f"{path}: marks[{index}] has unrecognised key(s) {unknown} for a {kind} mark"
            )
        if kind == "heatmap":
            declared = mark.get("color_map")
            if declared is not None and declared not in COLOR_MAPS:
                raise InvalidModel(
                    f"{path}: marks[{index}].color_map is {declared!r}, "
                    f"expected one of {sorted(COLOR_MAPS)}"
                )
    return model


def _expect_object(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidModel(f"{where}: expected an object, not {type(value).__name__}")
    # `isinstance` narrows to `dict[Any, Any]`; the JSON reader only ever produces
    # string keys, and saying so here keeps strict typing honest at one place.
    return cast("dict[str, Any]", value)


def _number(value: Any, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidModel(f"{where}: expected a number, not {value!r}")
    return float(value)


def _number_list(values: Any, where: str) -> list[float]:
    if not isinstance(values, list):
        raise InvalidModel(f"{where}: expected a list of numbers")
    return [_number(value, f"{where}[{position}]") for position, value in enumerate(values)]


def _points(mark: dict[str, Any], where: str) -> list[tuple[float, float]]:
    points = mark.get("points")
    if not isinstance(points, list):
        raise InvalidModel(f"{where}.points: expected a list of [x, y] pairs")
    out: list[tuple[float, float]] = []
    for position, point in enumerate(points):
        if not isinstance(point, list) or len(point) != 2:
            raise InvalidModel(f"{where}.points[{position}]: expected [x, y]")
        out.append(
            (
                _number(point[0], f"{where}.points[{position}][0]"),
                _number(point[1], f"{where}.points[{position}][1]"),
            )
        )
    return out


def _error_arrays(mark: dict[str, Any], where: str) -> list[tuple[str, list[float]]]:
    """The declared error magnitudes, as `(shape, magnitudes)`.

    Both shapes at once is left to the check that reports it, so a caller sees one
    finding naming the reason rather than an arbitrary precedence rule.
    """
    declared: list[tuple[str, list[float]]] = []
    if mark.get("y_err") is not None:
        declared.append(("symmetric", _number_list(mark["y_err"], f"{where}.y_err")))
    if mark.get("y_err_asymmetric") is not None:
        pairs = mark["y_err_asymmetric"]
        if not isinstance(pairs, list):
            raise InvalidModel(f"{where}.y_err_asymmetric: expected a list of [lower, upper]")
        flat: list[float] = []
        for position, pair in enumerate(pairs):
            if not isinstance(pair, list) or len(pair) != 2:
                raise InvalidModel(f"{where}.y_err_asymmetric[{position}]: expected [lower, upper]")
            flat.append(_number(pair[0], f"{where}.y_err_asymmetric[{position}][0]"))
            flat.append(_number(pair[1], f"{where}.y_err_asymmetric[{position}][1]"))
        declared.append(("asymmetric", flat))
    return declared


def _series_of(mark: dict[str, Any], where: str) -> list[tuple[str, list[float]]]:
    """`(label, values)` for each series: one for a bar, one per entry for a group."""
    if mark["kind"] == "bar":
        return [("bar mark", _number_list(mark.get("values"), f"{where}.values"))]
    series = mark.get("series")
    if not isinstance(series, list):
        # An *empty* list is readable — it declares nothing to draw, which is a
        # finding (`empty-chart`), not a member the loader cannot read.
        raise InvalidModel(f"{where}.series: expected a list of series")
    out: list[tuple[str, list[float]]] = []
    for position, one in enumerate(series):
        _expect_object(one, f"{where}.series[{position}]")
        unknown = sorted(key for key in one if key not in SERIES_FIELDS)
        if unknown:
            # `colour` for `color` was accepted and dropped: the figure was
            # inspected as if the key were absent.
            raise InvalidModel(
                f"{where}.series[{position}] has unrecognised key(s) {unknown} for a "
                f"series, expected one of {sorted(SERIES_FIELDS)}"
            )
        out.append(
            (
                f"series {position}",
                _number_list(one.get("values"), f"{where}.series[{position}].values"),
            )
        )
    return out


def _matrix(mark: dict[str, Any], where: str) -> list[list[float]]:
    """The declared matrix, as rows of numbers."""
    rows = mark.get("values")
    if not isinstance(rows, list):
        raise InvalidModel(f"{where}.values: expected a list of rows")
    out: list[list[float]] = []
    for position, row in enumerate(rows):
        out.append(_number_list(row, f"{where}.values[{position}]"))
    return out


def _labels(mark: dict[str, Any], field: str, where: str) -> list[str] | None:
    declared = mark.get(field)
    if declared is None:
        return None
    if not isinstance(declared, list) or not all(isinstance(name, str) for name in declared):
        raise InvalidModel(f"{where}.{field}: expected a list of strings")
    return cast("list[str]", declared)


def inspect_model(model: dict[str, Any], name: str = "figure") -> Report:
    """Check a chart declaration and report in this tool's own codes."""
    marks: list[dict[str, Any]] = model.get("marks", [])
    report = Report(
        name=name,
        subject=f"figure: {len(marks)} marks (declared)",
        details=[f"{len(marks)} marks", "declaration only — nothing was rendered"],
    )
    problems: list[Problem] = []

    def report_problem(
        code: str,
        message: str,
        target: str | None = None,
        identity: tuple[str, ...] = (),
    ) -> None:
        problems.append(Problem(MODEL_CODES[code], code, message, target=target, identity=identity))

    if not marks:
        report_problem("empty-chart", "the figure declares no marks, so there is nothing to read")

    logged = model.get("x_scale") == "log" or model.get("y_scale") == "log"
    if model.get("y_min") is not None or model.get("y_scale") == "log":
        for index, mark in enumerate(marks):
            if mark.get("kind") == "heatmap":
                # A heatmap's rows are its y axis, so a start or a log scale cannot
                # apply — the renderer that owns the model refuses the same
                # declaration, and this route reported it clean.
                report_problem(
                    "inapplicable-axis-setting",
                    "a heatmap's rows are its y axis, so `y_min` and a log scale "
                    "cannot apply to it",
                    f"m[{index}]",
                )
                break
    minimum = model.get("y_min")
    if minimum is not None:
        minimum = _number(minimum, f"{name}: y_min")

    # Two marks cannot both name one axis: a row label belongs to the row it is
    # next to, and picking one set would caption the other's data with it.
    named: list[list[str]] = []
    for mark in marks:
        if mark["kind"] == "heatmap":
            labels = _labels(mark, "row_labels", f"{name}: marks")
            if labels is not None:
                named.append(labels)

    for index, mark in enumerate(marks):
        kind = mark["kind"]
        target = f"m[{index}]"
        where = f"{name}: marks[{index}]"

        if kind == "heatmap":
            rows = _matrix(mark, where)
            if not rows or any(not row for row in rows):
                report_problem(
                    "empty-chart",
                    "heatmap mark declares no cells, so there is nothing to draw",
                    target,
                )
                continue
            width = len(rows[0])
            for position, row in enumerate(rows):
                if len(row) != width:
                    report_problem(
                        "mismatched-lengths",
                        f"heatmap row {position} has {len(row)} cells for {width} columns",
                        target,
                    )
            if any(not math.isfinite(value) for row in rows for value in row):
                report_problem(
                    "non-finite-value", "heatmap declares a cell that cannot be placed", target
                )
            row_labels = _labels(mark, "row_labels", where)
            if row_labels is not None and len(row_labels) != len(rows):
                report_problem(
                    "mismatched-lengths",
                    f"heatmap declares {len(row_labels)} row labels for {len(rows)} rows",
                    target,
                )
            col_labels = _labels(mark, "col_labels", where)
            if col_labels is not None and len(col_labels) != width:
                report_problem(
                    "mismatched-lengths",
                    f"heatmap declares {len(col_labels)} column labels for {width} columns",
                    target,
                )
            continue

        if kind in ("line", "scatter"):
            points = _points(mark, where)
            if not points:
                report_problem("empty-chart", f"{kind} mark declares no points to draw", target)
            if kind == "line" and len(points) == 1:
                report_problem(
                    "short-line",
                    "a line needs at least two points, and this one has 1",
                    target,
                )
            coordinates = [value for point in points for value in point]
            declared = _error_arrays(mark, where)
            if len(declared) == 2:
                report_problem(
                    "two-error-shapes",
                    f"{kind} mark declares symmetric and asymmetric error bars; one "
                    "drawing cannot mean both",
                    target,
                )
            for shape, magnitudes in declared:
                expected = len(points) if shape == "symmetric" else len(points) * 2
                if len(magnitudes) != expected:
                    count = len(magnitudes) if shape == "symmetric" else len(magnitudes) // 2
                    report_problem(
                        "mismatched-lengths",
                        f"{kind} mark declares {count} {shape} error magnitudes for "
                        f"{len(points)} points",
                        target,
                    )
                if any(value < 0 for value in magnitudes):
                    report_problem(
                        "negative-error", f"{kind} mark has a negative error magnitude", target
                    )
                # A magnitude is drawn too: `NaN` in a `y_err` array passed the
                # negative test (every comparison is false) and the coordinate test
                # (it is not a coordinate), so the reader accepted the file and the
                # report was clean while the sibling route refused to parse it.
                if any(not math.isfinite(value) for value in magnitudes):
                    report_problem(
                        "non-finite-value",
                        f"{kind} mark declares an error magnitude that cannot be placed",
                        target,
                    )
            if any(not math.isfinite(value) for value in coordinates):
                report_problem(
                    "non-finite-value",
                    f"{kind} mark draws a coordinate that cannot be placed",
                    target,
                )
            if logged and any(value <= 0 for value in coordinates):
                report_problem(
                    "log-nonpositive", "a log axis cannot place a non-positive value", target
                )
            continue

        categories = mark.get("categories")
        if not isinstance(categories, list) or not all(
            isinstance(label, str) for label in categories
        ):
            raise InvalidModel(f"{where}.categories: expected a list of strings")
        if not categories:
            report_problem("empty-chart", "a bar mark declares no categories to draw", target)
        read = _series_of(mark, where)
        if kind == "grouped_bar" and not read:
            report_problem("empty-chart", "grouped_bar mark declares no series to draw", target)
        for label, values in read:
            if len(values) != len(categories):
                report_problem(
                    "mismatched-lengths",
                    f"{label} has {len(values)} values for {len(categories)} categories",
                    target,
                )
            if any(not math.isfinite(value) for value in values):
                report_problem(
                    "non-finite-value", "a bar declares a value that cannot be placed", target
                )
            if logged and any(value <= 0 for value in values):
                report_problem(
                    "log-nonpositive", "a log axis cannot place a non-positive value", target
                )
        if minimum is not None and minimum > 0:
            report_problem(
                "truncated-baseline",
                f"bars start at y={minimum:g}, not 0, so their lengths no longer mean their values",
                target,
            )

    if len(named) > 1 and any(labels != named[0] for labels in named):
        # The finding is about the *pair*: which two marks disagree. A figure whose
        # ambiguity involves different marks is different debt, so the two marks
        # are its identity.
        first = named[0]
        for labels in named[1:]:
            if labels != first:
                report_problem(
                    "ambiguous-labels",
                    "two marks declare different row labels for the same axis, so one "
                    "would caption the other's data",
                    # The identity is the two rival namings themselves, not their
                    # positions: a figure whose rows are named differently is a
                    # different disagreement, and replacing one partner for another
                    # must read as new debt.
                    identity=("ambiguous-labels", ", ".join(first), ", ".join(labels)),
                )

    if marks and not model.get("title"):
        report_problem("no-title", "the figure has no title, so a reader cannot tell what it shows")
    if marks:
        # An empty declaration is already `empty-chart`; complaining about its axis
        # labels as well would bury the one finding that matters.
        if not model.get("x_label"):
            report_problem("no-xlabel", "the x axis has no label")
        if not model.get("y_label"):
            report_problem("no-ylabel", "the y axis has no label")

    report.problems = problems
    return report
