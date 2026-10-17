"""Exercise the small public surface and the fallbacks the tools rely on.

These are the bits that no domain test happened to touch: the `missing` helper,
the diagram's label truncation, the old-Pillow font fallback, the CLI's
missing-file branch, and `scene_tool`'s DPI-aware save.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from gxcore import diagram, storyboard, testing
from gxcore.cli import Tool, run
from gxcore.model import ERROR, INFO, Problem, Report
from gxcore.toolkit import scene_tool
from PIL import Image, ImageDraw, ImageFont


def test_missing_lists_only_the_absent_codes():
    report = Report("x", problems=[Problem(INFO, "a", "m"), Problem(ERROR, "c", "m")])
    assert testing.missing(report, ["a", "b", "c"]) == ["b"]


def test_assert_quiet_raises_when_the_code_is_present():
    report = Report("x", problems=[Problem(ERROR, "boom", "m")])
    with pytest.raises(AssertionError):
        testing.assert_quiet(report, "boom")


def test_messages_targets_and_count():
    report = Report(
        "x",
        problems=[
            Problem(ERROR, "a", "one", target="t1"),
            Problem(INFO, "a", "two", target="t2"),
        ],
    )
    assert testing.messages(report) == ["one", "two"]
    assert testing.targets(report, "a") == ["t1", "t2"]
    assert testing.count(report, "a") == 2


def test_diagram_fit_keeps_a_label_that_fits():
    draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    _font, shown = diagram._fit(draw, "hi", max_width=100, size=20)
    assert shown == "hi"


def test_diagram_fit_truncates_a_label_that_cannot_fit():
    draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    _font, shown = diagram._fit(draw, "x" * 300, max_width=6, size=40)
    assert shown.endswith("…")
    assert len(shown) < 300


def test_storyboard_survives_a_pillow_without_a_sized_default(monkeypatch, tmp_path):
    real = ImageFont.load_default

    def load_default(*args, **kwargs):
        if args or kwargs:
            raise TypeError("load_default(size=) is new in Pillow 10")
        return real()

    monkeypatch.setattr(ImageFont, "load_default", load_default)
    img = Image.new("RGB", (120, 90), (255, 255, 255))
    problem = Problem(ERROR, "x", "m", bbox=(10.0, 10.0, 40.0, 30.0))
    out = storyboard.annotate(img, [problem], tmp_path / "sb.png")
    assert out.exists() and out.stat().st_size > 0


def test_cli_reports_a_missing_file(tmp_path, capsys):
    def load(path):
        raise FileNotFoundError(path)

    tool = Tool(
        name="t",
        description="d",
        load=load,
        inspect=lambda a: Report("x"),
        render=lambda a, o, d: Path("x"),
    )
    assert run(tool, ["inspect", str(tmp_path / "nope.py")]) == 2
    assert "no such file" in capsys.readouterr().err


def test_scene_tool_render_honours_dpi(tmp_path):
    main, _tool = scene_tool(
        name="t",
        description="d",
        load=lambda p: ("artifact", None),
        inspect=lambda a: Report("x"),
        to_image=lambda a: Image.new("RGB", (8, 8), (1, 2, 3)),
    )
    out = tmp_path / "r.png"
    assert main(["render", str(tmp_path / "a.py"), "-o", str(out), "--dpi", "72"]) == 0
    assert out.exists()
    assert Image.open(out).size == (8, 8)


def test_a_label_with_a_newline_is_flattened_rather_than_losing_the_image():
    """Pillow cannot measure multi-line text, and a name is arbitrary text.

    Measured: a dependency graph with a module named `"a\\nb"` lost its whole
    storyboard to `ValueError: can't measure length of multiline text`.
    """
    from gxcore.diagram import Node as DiagramNode
    from gxcore.diagram import render
    from gxcore.toolkit import one_line

    assert one_line("line1\nline2") == "line1 line2"
    assert one_line("a\tb\rc") == "a b c"
    assert one_line("plain") == "plain"
    assert render([DiagramNode("n", "line1\nline2")], []).size[0] > 0


def test_a_finding_with_an_unplaceable_box_does_not_lose_the_whole_storyboard():
    from gxcore.model import ERROR, Problem
    from gxcore.storyboard import labelled_boxes

    problems = [
        Problem(ERROR, "e", "m", bbox=(float("nan"), 10.0, 20.0, 30.0)),
        Problem(ERROR, "f", "m", bbox=(1.0, 2.0, 3.0, 4.0)),
    ]
    boxes = labelled_boxes(problems, height=100)
    # The number keeps the sorted position the printed list shows; only the
    # rectangle is dropped.
    assert [box.numbers for box in boxes] == [(2,)]
