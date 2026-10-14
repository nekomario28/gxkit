"""Prove every chartgx check fires on a chart that has the defect and stays quiet otherwise.

A check that never fails is not a check. Each test builds the defect in a real
matplotlib figure and asserts the matching problem code appears (or does not).
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
from chartgx import inspect_figure
from gxcore import ERROR, INFO, WARN
from gxcore.testing import assert_fires, assert_quiet, codes


def fresh():
    plt.close("all")


def report(fig):
    return inspect_figure(fig)


# --------------------------------------------------------------------------- #
# misleading encoding
# --------------------------------------------------------------------------- #


def test_truncated_bar_baseline_is_an_error():
    fresh()
    fig, ax = plt.subplots()
    ax.bar(["a", "b", "c"], [42, 51, 47])
    ax.set_ylim(40, 55)
    ax.set_title("t")
    ax.set_xlabel("x")
    ax.set_ylabel("y (£)")
    assert_fires(report(fig), "truncated-baseline", ERROR)


def test_bar_from_zero_is_clean():
    fresh()
    fig, ax = plt.subplots()
    ax.bar(["a", "b", "c"], [42, 51, 47])
    ax.set_ylim(0, 55)
    ax.set_title("t")
    ax.set_xlabel("x")
    ax.set_ylabel("y (£)")
    assert_quiet(report(fig), "truncated-baseline")
    assert report(fig).errors == 0


def test_horizontal_bar_truncated_x_baseline():
    fresh()
    fig, ax = plt.subplots()
    ax.barh(["a", "b", "c"], [42, 51, 47])
    ax.set_xlim(40, 55)
    ax.set_title("t")
    ax.set_xlabel("x (£)")
    ax.set_ylabel("y")
    assert_fires(report(fig), "truncated-baseline", ERROR)


def test_log_nonpositive():
    fresh()
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [0, 10, 100])
    ax.set_yscale("log")
    ax.set_title("t")
    assert_fires(report(fig), "log-nonpositive", ERROR)


def test_clipped_data():
    fresh()
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2, 3], [0, 5, 9, 12])
    ax.set_ylim(0, 5)
    ax.set_title("t")
    assert_fires(report(fig), "clipped-data", WARN)


def test_constant_series():
    fresh()
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3, 4], [5, 5, 5, 5])
    ax.set_title("t")
    assert_fires(report(fig), "constant-series", WARN)


def test_reference_line_is_not_a_constant_series():
    fresh()
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3, 4], [1, 3, 2, 5])
    ax.axhline(0, color="grey")
    ax.set_title("t")
    assert_quiet(report(fig), "constant-series")


# --------------------------------------------------------------------------- #
# broken layout
# --------------------------------------------------------------------------- #


def test_empty_axes_is_an_error():
    fresh()
    fig, ax = plt.subplots()
    ax.set_title("t")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    assert_fires(report(fig), "empty-chart", ERROR)


def test_overlapping_text():
    fresh()
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 4, 9])
    ax.set_title("t")
    ax.text(0.5, 0.5, "alpha", transform=ax.transAxes, fontsize=20)
    ax.text(0.5, 0.5, "beta", transform=ax.transAxes, fontsize=20)
    assert_fires(report(fig), "text-overlap", ERROR)


def test_clipped_text():
    fresh()
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 4, 9])
    ax.set_title("A title so long it cannot possibly fit inside the figure " * 3)
    assert_fires(report(fig), "clipped-text", ERROR)


def test_small_text():
    fresh()
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 4, 9])
    ax.set_title("t", fontsize=6)
    assert_fires(report(fig), "small-text", INFO)


def test_legend_covers_data():
    fresh()
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2, 3, 4], [0, 1, 2, 3, 4], label="series")
    ax.set_title("t")
    ax.legend(loc="center")
    assert_fires(report(fig), "legend-covers", WARN)


# --------------------------------------------------------------------------- #
# missing context / deceptive composition
# --------------------------------------------------------------------------- #


def test_missing_title_and_labels():
    fresh()
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 4, 9])
    r = report(fig)
    assert_fires(r, "no-title", WARN)
    assert_fires(r, "no-xlabel", WARN)
    assert_fires(r, "no-ylabel", WARN)


def test_shared_x_only_needs_one_label():
    fresh()
    fig, (a, b) = plt.subplots(2, 1, sharex=True)
    a.bar(["x", "y"], [1, 2])
    a.set_ylabel("a (£)")
    b.plot(["x", "y"], [2, 1])
    b.set_xlabel("group")
    b.set_ylabel("b (%)")
    fig.suptitle("t")
    assert_quiet(report(fig), "no-xlabel")


def test_dual_axis():
    fresh()
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 4, 9])
    ax.set_title("t")
    ax2 = ax.twinx()
    ax2.plot([1, 2, 3], [9, 4, 1])
    assert_fires(report(fig), "dual-axis", WARN)


def test_too_many_series():
    fresh()
    fig, ax = plt.subplots()
    for i in range(12):
        ax.plot([0, 1], [i, i + 1])
    ax.set_title("t")
    assert_fires(report(fig), "too-many-series", WARN)


def test_pie_too_many_slices():
    fresh()
    fig, ax = plt.subplots()
    ax.pie([1] * 8)
    ax.set_title("t")
    assert_fires(report(fig), "pie-slices", WARN)


# --------------------------------------------------------------------------- #
# report shape
# --------------------------------------------------------------------------- #


def test_report_has_details_and_stable_codes():
    fresh()
    fig, ax = plt.subplots()
    ax.bar(["a", "b"], [1, 2])
    r = report(fig)
    assert r.details and r.details[0].startswith("ax[0]")
    assert {"empty-chart", "truncated-baseline"} & {c for _, c in codes(r)} == set()
    assert isinstance(r.as_dict()["problems"], list)


# --------------------------------------------------------------------------- #
# axis orientation
# --------------------------------------------------------------------------- #


def test_inverted_y_axis_is_flagged():
    fresh()
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 4, 9])
    ax.set_ylim(10, 0)
    ax.set_title("t")
    ax.set_xlabel("x")
    ax.set_ylabel("y (m)")
    assert_fires(report(fig), "inverted-axis", WARN)


def test_a_normal_axis_is_quiet():
    fresh()
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 4, 9])
    ax.set_ylim(0, 10)
    ax.set_title("t")
    ax.set_xlabel("x")
    ax.set_ylabel("y (m)")
    assert_quiet(report(fig), "inverted-axis")
