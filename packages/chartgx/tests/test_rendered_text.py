"""Regressions from a real report task, checked against actual Text.draw calls."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import pytest
from chartgx import checks, inspect_figure
from matplotlib.text import Text
from matplotlib.ticker import FixedLocator, FuncFormatter

TITLE = "Observed CI job durations (jobs run in parallel; not workflow elapsed time)"
JOBS = [
    "test",
    "wheels (macos-latest, aarch64-apple-darwin, off)",
    "wheels (ubuntu-latest, x86_64, auto)",
    "wheels (windows-latest, x86_64-pc-windows-msvc, off)",
    "wheels (ubuntu-24.04-arm, aarch64, auto)",
]
SECONDS = [185, 163, 171, 274, 170]


def _job_chart(title):
    # The naturally generated pilot chart, without its savefig side effect. These
    # are parallel jobs' individual durations, not workflow elapsed time.
    order = sorted(range(len(JOBS)), key=SECONDS.__getitem__)
    values = [SECONDS[i] for i in order]
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.barh(range(len(order)), values, color="#4C72B0", height=0.6)
    ax.set_yticks(range(len(order)), [JOBS[i] for i in order], fontsize=8)
    ax.set_xlabel("Wall-clock duration (seconds)", fontsize=9)
    ax.set_title(title, fontsize=10)
    ax.tick_params(axis="x", labelsize=8)
    ax.set_xlim(0, max(values) * 1.15)
    for bar, value in zip(bars, values, strict=True):
        ax.text(
            bar.get_width() + max(values) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{value}s",
            va="center",
            fontsize=8,
        )
    fig.tight_layout()
    return fig, ax


def _record_draws(monkeypatch):
    drawn = set()
    original = Text.draw

    def record(text, renderer):
        if text.get_visible() and text.get_text().strip():
            drawn.add(text)
        return original(text, renderer)

    monkeypatch.setattr(Text, "draw", record)
    return drawn


def test_valid_pilot_chart_has_no_errors_from_undrawn_tick():
    fig, ax = _job_chart("CI job wall-clock durations")
    try:
        # A locator offers 350, outside the view, with get_visible() == True.
        # Matplotlib never calls its draw method. It must not block a valid chart.
        offered = ax.get_xticklabels()
        assert any(t.get_text() == "350" and t.get_visible() for t in offered)
        report = inspect_figure(fig)
        assert report.errors == 0, report.problems
    finally:
        plt.close(fig)


def test_real_title_clipping_is_actionable_and_wrapping_repairs_it():
    fig, ax = _job_chart(TITLE)
    try:
        report = inspect_figure(fig)
        clipped = [p for p in report.problems if p.code == "clipped-text"]
        assert len(clipped) == 1, clipped
        assert clipped[0].label.startswith("Observed CI job durations")
        assert "ax.set_title" in clipped[0].message
        assert "\\n" in clipped[0].message
        assert "axis limits" in clipped[0].message
        values = [bar.get_width() for bar in ax.patches]
        limits = ax.get_xlim()
        # Execute the suggested class of repair, preserving every title word,
        # job, duration and data limit. A message-only assertion is not enough.
        ax.set_title(TITLE.replace(" (", "\n("), fontsize=10)
        fig.tight_layout()
        assert inspect_figure(fig).errors == 0
        assert [bar.get_width() for bar in ax.patches] == values
        assert ax.get_xlim() == limits
        assert ax.get_title().replace("\n", " ") == TITLE
    finally:
        plt.close(fig)


@pytest.mark.parametrize("axis_name", ["x", "y"])
@pytest.mark.parametrize(
    ("scale", "reverse"), [("linear", False), ("linear", True), ("log", False), ("log", True)]
)
def test_selected_ticks_match_actual_draw_calls(monkeypatch, axis_name, scale, reverse):
    fig, ax = plt.subplots()
    try:
        ax.plot([1, 2], [1, 2])
        axis = getattr(ax, f"{axis_name}axis")
        getattr(ax, f"set_{axis_name}scale")(scale)
        limits = (1, 100) if scale == "log" else (0, 2)
        major = [0.1, 1, 10, 100, 1000] if scale == "log" else [-1, 0, 1, 2, 3]
        minor = [0.5, 5, 50, 500] if scale == "log" else [-0.5, 0.5, 1.5, 2.5]
        getattr(ax, f"set_{axis_name}lim")(*(limits[::-1] if reverse else limits))
        axis.set_major_locator(FixedLocator(major))
        axis.set_minor_locator(FixedLocator(minor))
        axis.set_major_formatter(FuncFormatter(lambda value, pos: f"major:{value:g}"))
        axis.set_minor_formatter(FuncFormatter(lambda value, pos: f"minor:{value:g}"))
        # Both sides count; a public get_*ticklabels() also omits minor labels.
        ax.tick_params(axis=axis_name, which="both", labeltop=True, labelright=True)
        drawn = _record_draws(monkeypatch)
        fig.canvas.draw()
        expected = {t for t in drawn if t.get_text().startswith(("major:", "minor:"))}
        candidates = {
            t
            for role, t in checks._texts(ax)
            if role == "tick" and t.get_visible() and t.get_text().startswith(("major:", "minor:"))
        }
        assert expected
        assert candidates == expected
        assert any(t.get_text().startswith("minor:") for t in candidates)
    finally:
        plt.close(fig)


@pytest.mark.parametrize("hidden", [False, True])
@pytest.mark.parametrize("axis_visible", [False, True])
def test_3d_axis_labels_follow_the_projection_visibility(monkeypatch, hidden, axis_visible):
    fig = plt.figure()
    ax = fig.add_subplot(projection="3d")
    try:
        ax.plot([0, 1], [0, 1], [0, 1])
        ax.set_xlabel("projected x", fontsize=6)
        ax.set_ylabel("projected y", fontsize=6)
        ax.xaxis.set_visible(axis_visible)
        assert not ax.axison  # 3D draws its own axes, independently of 2D's flag.
        if hidden:
            ax.set_axis_off()
        drawn = _record_draws(monkeypatch)
        fig.canvas.draw()
        labels = {ax.xaxis.label, ax.yaxis.label}
        selected = {t for _, t in checks._texts(ax)} & labels
        assert selected == drawn & labels
        report = inspect_figure(fig)
        small_labels = {p.label for p in report.problems if p.code == "small-text"}
        assert ("projected x" in small_labels) is not hidden
        assert ("projected y" in small_labels) is not hidden
    finally:
        plt.close(fig)


@pytest.mark.parametrize("hidden", ["axis", "axes", "axis-off", "tick"])
def test_hidden_ancestors_do_not_contribute_text(monkeypatch, hidden):
    fig, ax = plt.subplots()
    try:
        ax.plot([0, 1], [0, 1])
        ax.set_title("t")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        if hidden == "axis":
            ax.xaxis.set_visible(False)
        elif hidden == "axes":
            ax.set_visible(False)
        elif hidden == "axis-off":
            ax.set_axis_off()
        else:
            for tick in ax.xaxis.get_major_ticks():
                tick.set_visible(False)
        drawn = _record_draws(monkeypatch)
        fig.canvas.draw()
        selected = {t for _, t in checks._texts(ax) if t.get_visible() and t.get_text().strip()}
        assert selected == drawn
    finally:
        plt.close(fig)
