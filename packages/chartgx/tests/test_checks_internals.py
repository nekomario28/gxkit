"""The chartgx internals that real figures rarely drive: defensive guards and
the branches no example reaches (log x-axis, red/green, no-units, and so on).

A guard that swallows a matplotlib introspection failure is exactly the code
that can silently disable a check, so each one is exercised.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
from chartgx import checks
from gxcore import ERROR, INFO, Problem, Report


def _boom(*args, **kwargs):
    raise RuntimeError("boom")


# --------------------------------------------------------------------------- #
# defensive guards
# --------------------------------------------------------------------------- #


def test_bbox_returns_none_when_the_text_cannot_be_measured():
    class Text:
        def get_text(self):
            raise RuntimeError("no text")

    assert checks._bbox(Text(), None) is None


def test_series_count_defaults_to_one_when_containers_fail():
    class Axes:
        @property
        def containers(self):
            raise RuntimeError("no containers")

    assert checks._series_count(Axes(), "bar") == 1


def test_data_bbox_is_none_without_artists():
    class Axes:
        lines: tuple = ()
        collections: tuple = ()

    assert checks._data_bbox(Axes(), None) is None


def test_data_bbox_skips_an_artist_that_cannot_be_measured():
    class Artist:
        def get_window_extent(self, renderer):
            raise RuntimeError("no box")

    class Axes:
        lines = (Artist(),)
        collections: tuple = ()

    assert checks._data_bbox(Axes(), None) is None


def test_twins_is_empty_when_there_is_no_twin_registry():
    class Axes:
        @property
        def _twinned_axes(self):
            raise RuntimeError("no registry")

    assert checks._twins(Axes()) == []


def test_shared_x_has_label_is_false_when_the_registry_fails():
    class Axes:
        def get_shared_x_axes(self):
            raise RuntimeError("no registry")

    assert checks._shared_x_has_label(Axes()) is False


def test_hex_to_rgb_rejects_a_bad_hex_and_a_named_colour():
    assert checks._hex_to_rgb("#zzzzzz") is None
    assert checks._hex_to_rgb("red") is None
    assert checks._is_green("red") is False


def test_bar_baseline_returns_when_there_are_no_rectangles():
    class Axes:
        patches: tuple = ()

    out: list[Problem] = []
    checks._check_bar_baseline(Axes(), 0, "bar", out)
    assert out == []


def test_constant_series_skips_a_line_that_cannot_be_read(monkeypatch):
    fig, ax = plt.subplots()
    (line,) = ax.plot([1, 2, 3], [5, 5, 5])
    monkeypatch.setattr(line, "get_ydata", _boom)
    out: list[Problem] = []
    checks._check_constant(ax, 0, out)
    plt.close(fig)
    assert out == []


def test_log_check_skips_a_line_that_cannot_be_read(monkeypatch):
    fig, ax = plt.subplots()
    (line,) = ax.plot([1, 2, 3], [1, 10, 100])
    ax.set_yscale("log")
    monkeypatch.setattr(line, "get_ydata", _boom)
    out: list[Problem] = []
    checks._check_log(ax, 0, out)
    plt.close(fig)
    assert out == []


def test_clipped_data_skips_an_empty_line():
    fig, ax = plt.subplots()
    ax.plot([], [])
    out: list[Problem] = []
    checks._check_clipped_data(ax, 0, out)
    plt.close(fig)
    assert out == []


def test_text_items_tolerates_a_text_without_a_fontsize(monkeypatch):
    fig, ax = plt.subplots()
    ax.plot([1, 2], [1, 2])
    ax.set_title("t")
    fig.canvas.draw()
    monkeypatch.setattr(ax.title, "get_fontsize", _boom)
    items = checks._text_items(ax, fig.canvas.get_renderer())
    plt.close(fig)
    assert any(item.fontsize is None for item in items)


def test_legend_covers_returns_when_the_legend_cannot_be_measured(monkeypatch):
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1], label="s")
    legend = ax.legend()
    monkeypatch.setattr(legend, "get_window_extent", _boom)
    out: list[Problem] = []
    checks._check_legend_covers(ax, 0, object(), out)
    plt.close(fig)
    assert out == []


def test_locate_structural_skips_an_out_of_range_target():
    report = Report("x", problems=[Problem(ERROR, "empty-chart", "m", target="ax[9]")])
    checks._locate_structural(report, [], object())
    assert report.problems[0].bbox is None


# --------------------------------------------------------------------------- #
# branches a real figure can reach
# --------------------------------------------------------------------------- #


def test_units_note_fires_for_a_label_without_a_unit():
    class Axes:
        patches: tuple = ()

        def get_ylabel(self):
            return "value"

        def get_xlabel(self):
            return "x"

    out: list[Problem] = []
    checks._check_units_note(Axes(), 0, "line", out)
    assert [p.code for p in out] == ["no-units"]
    assert out[0].severity == INFO


def test_log_x_axis_with_a_nonpositive_value():
    fig, ax = plt.subplots()
    ax.plot([0, 1, 10], [1, 2, 3])
    ax.set_xscale("log")
    ax.set_title("t")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    assert any(p.code == "log-nonpositive" for p in checks.inspect_figure(fig).problems)
    plt.close(fig)


def test_red_and_green_series_are_flagged():
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 2, 3], color="#cc2222")
    ax.plot([1, 2, 3], [3, 2, 1], color="#22aa22")
    ax.set_title("t")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    assert any(p.code == "red-green" for p in checks.inspect_figure(fig).problems)
    plt.close(fig)


def test_legend_over_a_bar_chart_needs_no_data_bbox():
    fig, ax = plt.subplots()
    ax.bar(["a", "b"], [1, 2], label="bars")
    ax.legend()
    ax.set_title("t")
    ax.set_xlabel("x")
    ax.set_ylabel("y (m)")
    assert isinstance(checks.inspect_figure(fig).problems, list)
    plt.close(fig)


def test_log_x_check_skips_a_line_that_cannot_be_read(monkeypatch):
    fig, ax = plt.subplots()
    (line,) = ax.plot([1, 2, 3], [1, 2, 3])
    ax.set_xscale("log")
    monkeypatch.setattr(line, "get_xdata", _boom)
    out: list[Problem] = []
    checks._check_log(ax, 0, out)
    plt.close(fig)
    assert out == []
