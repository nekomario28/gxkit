"""chartgx's loader fallback and its `main` entry point."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
from chartgx.loader import load_figure
from chartgx.tool import main


def test_loader_falls_back_to_an_already_open_figure(tmp_path):
    plt.close("all")
    src = tmp_path / "open.py"
    src.write_text("import matplotlib.pyplot as plt\nplt.plot([1, 2, 3], [3, 2, 1])\n")
    fig, module = load_figure(src)
    assert fig is not None
    assert module is None  # no module-level `fig`, so the open figure was used
    plt.close("all")


def test_main_inspects_the_good_example():
    example = Path(__file__).resolve().parents[1] / "examples" / "good_chart.py"
    assert main(["inspect", str(example), "--no-storyboard"]) == 0


def test_loader_reports_a_missing_file(tmp_path):
    import pytest

    with pytest.raises(FileNotFoundError):
        load_figure(tmp_path / "nope.py")


def test_figure_name_falls_back_to_the_given_stem():
    from chartgx.tool import _figure_name

    plt.close("all")
    fig, _ax = plt.subplots()
    assert _figure_name(fig, "stem") == "stem"
    plt.close("all")


def test_a_check_that_throws_does_not_hide_the_others(monkeypatch):
    import chartgx.checks as checks

    plt.close("all")
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [2, 4, 6])
    ax.set_title("t")

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(checks, "_check_title", boom)
    assert checks.inspect_figure(fig) is not None
    plt.close("all")


def test_figure_name_prefers_the_suptitle():
    from chartgx.tool import _figure_name

    plt.close("all")
    fig, _ax = plt.subplots()
    fig.suptitle("Big title")
    assert _figure_name(fig, "stem") == "Big title"
    plt.close("all")


def test_inspect_survives_a_renderer_that_cannot_be_built(monkeypatch):
    import chartgx.checks as checks

    plt.close("all")
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [2, 4, 6])
    ax.set_title("t")

    def boom(fig):
        raise RuntimeError("no renderer")

    monkeypatch.setattr(checks, "_renderer", boom)
    assert checks.inspect_figure(fig) is not None
    plt.close("all")
