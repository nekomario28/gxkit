"""The chart-kind classifier decides which checks run.

`_classify` picks the branch that every kind-specific check keys on — a bar
misread as a line silently disables the baseline check, a pie misread skips the
slice limit. So each real plot type is drawn and the classifier must name it.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import pytest
from chartgx import inspect_figure
from chartgx.checks import _classify


def _kind(build) -> str:
    plt.close("all")
    _, ax = plt.subplots()
    build(ax)
    kind = _classify(ax)
    plt.close("all")
    return kind


CASES = {
    "line": lambda ax: ax.plot([1, 2, 3], [1, 4, 9]),
    "bar": lambda ax: ax.bar(["a", "b"], [1, 2]),
    "scatter": lambda ax: ax.scatter([1, 2, 3], [1, 4, 9]),
    "area": lambda ax: ax.fill_between([1, 2, 3], [1, 2, 3]),
    "pie": lambda ax: ax.pie([1, 2, 3]),
    "image": lambda ax: ax.imshow([[1, 2], [3, 4]]),
    "collection": lambda ax: ax.vlines([1, 2], [0, 0], [1, 2]),
    "empty": lambda ax: None,
}


@pytest.mark.parametrize("expected", sorted(CASES))
def test_classifier_names_the_plot_kind(expected):
    assert _kind(CASES[expected]) == expected


HEALTHY = {
    "line": lambda ax: ax.plot([1, 2, 3], [2, 4, 6]),
    "bar": lambda ax: ax.bar(["a", "b", "c"], [42, 51, 47]),
    "scatter": lambda ax: ax.scatter([1, 2, 3], [2, 4, 6]),
    "area": lambda ax: ax.fill_between([1, 2, 3], [1, 2, 3]),
}


@pytest.mark.parametrize("name", sorted(HEALTHY))
def test_a_healthy_chart_has_no_errors(name):
    plt.close("all")
    fig, ax = plt.subplots()
    HEALTHY[name](ax)
    ax.set_title("t")
    ax.set_xlabel("x (s)")
    ax.set_ylabel("y (m)")
    report = inspect_figure(fig)
    plt.close("all")
    assert report.errors == 0, [
        (p.code, p.message) for p in report.problems if p.severity == "error"
    ]
