from __future__ import annotations

import json

import pytest
from gxcore import ERROR, INFO, WARN, Problem, Report
from gxcore.cli import Tool, run
from gxcore.geometry import both_covered, clipped, covered, intersecting_pairs, overlap, union
from gxcore.model import sort_key
from gxcore.report import human, to_json
from gxcore.storyboard import annotate, safe_name, storyboard_path
from gxcore.testing import assert_fires, assert_quiet, codes, has
from PIL import Image

# --------------------------------------------------------------------------- #
# model
# --------------------------------------------------------------------------- #


def test_unknown_severity_is_rejected():
    with pytest.raises(ValueError, match="unknown severity"):
        Problem("fatal", "x", "y")


def test_errors_count_only_errors():
    r = Report(
        "n",
        problems=[
            Problem(ERROR, "a", "m"),
            Problem(WARN, "b", "m"),
            Problem(INFO, "c", "m"),
        ],
    )
    assert r.errors == 1


def test_sorted_puts_errors_first():
    r = Report(
        "n",
        problems=[
            Problem(INFO, "i", "m"),
            Problem(ERROR, "e", "m"),
            Problem(WARN, "w", "m"),
        ],
    )
    assert [p.severity for p in r.sorted()] == [ERROR, WARN, INFO]


def test_report_and_storyboard_share_one_order():
    # The invariant that makes box [n] in the image equal problem [n] in the text.
    problems = [
        Problem(INFO, "i", "m", target="zzz"),
        Problem(ERROR, "e", "m", target="bbb"),
        Problem(ERROR, "e2", "m", target="aaa"),
    ]
    assert Report("n", problems=problems).sorted() == sorted(problems, key=sort_key)


def test_as_dict_is_stable_and_omits_empty_fields():
    r = Report("n", subject="figure", problems=[Problem(ERROR, "e", "m")])
    d = r.as_dict()
    assert d["errors"] == 1
    assert d["problems"][0] == {"severity": "error", "code": "e", "message": "m"}


# --------------------------------------------------------------------------- #
# geometry
# --------------------------------------------------------------------------- #


def test_overlap_and_covered():
    a = (0, 0, 10, 10)
    b = (5, 5, 15, 15)
    assert overlap(a, b) == 25
    assert covered(a, b) == 0.25
    assert both_covered(a, b) == 0.25


def test_no_overlap_is_zero():
    assert overlap((0, 0, 1, 1), (5, 5, 6, 6)) == 0


def test_clipped_reports_edges():
    assert set(clipped((-5, 0, 10, 10), (0, 0, 20, 20))) == {"left"}


def test_union():
    assert union([(0, 0, 1, 1), (2, 2, 3, 3)]) == (0, 0, 3, 3)
    assert union([]) is None


def test_intersecting_pairs():
    boxes = [(0, 0, 10, 10), (1, 1, 11, 11), (50, 50, 60, 60)]
    pairs = intersecting_pairs(boxes)
    assert [p[:2] for p in pairs] == [(0, 1)]


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #


def test_human_no_problems():
    out = human("chart.py", Report("T"))
    assert "no problems" in out
    assert out.startswith("chart.py: T")


def test_human_lists_problems_with_codes():
    r = Report("T", subject="figure: 1 axes", problems=[Problem(ERROR, "bad", "it is bad")])
    out = human("chart.py", r)
    assert "[1] error" in out and "bad: it is bad" in out
    assert "1 problem (1 error)" in out


def test_json_roundtrips():
    r = Report("T", problems=[Problem(WARN, "w", "m")])
    d = json.loads(to_json(r, "/tmp/x.png"))
    assert d["storyboard"] == "/tmp/x.png"
    assert d["problems"][0]["code"] == "w"


# --------------------------------------------------------------------------- #
# storyboard
# --------------------------------------------------------------------------- #


def test_safe_name():
    assert safe_name("a b/c:d") == "a_b_c_d"
    assert safe_name("") == "artifact"
    assert len(safe_name("x" * 200)) <= 48


def test_storyboard_path():
    assert storyboard_path("My Chart").name == "My_Chart.storyboard.png"
    assert storyboard_path("x", "out.png").name == "out.png"


def test_annotate_draws_and_saves(tmp_path):
    img = Image.new("RGB", (200, 120), "white")
    p = Problem(ERROR, "e", "m", bbox=(10, 10, 60, 60))
    out = annotate(img, [p], tmp_path / "s.png", origin="bottom-left")
    assert out.exists()
    assert Image.open(out).size == (200, 120)


def test_annotate_top_left_origin(tmp_path):
    img = Image.new("RGB", (50, 50), "white")
    p = Problem(INFO, "i", "m", bbox=(1, 1, 10, 10))
    assert annotate(img, [p], tmp_path / "s.png", origin="top-left").exists()


def test_annotate_groups_colocated_problems(tmp_path):
    # Two faults on the same node must not hide each other under one box.
    img = Image.new("RGB", (120, 120), "white")
    box = (20, 20, 80, 80)
    problems = [
        Problem(ERROR, "e", "m", bbox=box),
        Problem(INFO, "i", "m", bbox=box),
    ]
    out = annotate(img, problems, tmp_path / "s.png", origin="top-left")
    assert out.exists()
    assert Image.open(out).size == (120, 120)


# --------------------------------------------------------------------------- #
# testing helpers
# --------------------------------------------------------------------------- #


def test_testing_helpers():
    r = Report("T", problems=[Problem(ERROR, "e", "m")])
    assert (ERROR, "e") in codes(r)
    assert has(r, "e", ERROR)
    assert not has(r, "e", WARN)
    assert_fires(r, "e", ERROR)
    assert_quiet(r, "other")
    with pytest.raises(AssertionError):
        assert_fires(r, "other")


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #


def _tool(tmp_path, with_image=True):
    from gxcore import ERROR as E

    def load(path):
        return "artifact"

    def inspect(art):
        return Report("R", subject="thing", problems=[Problem(E, "e", "m")])

    def render(art, out, dpi):
        out = out or Path(out)
        Image.new("RGB", (10, 10)).save(out)
        return out

    def to_image(art):
        return Image.new("RGB", (10, 10), "white")

    return Tool(
        "t",
        "d",
        load=load,
        inspect=inspect,
        render=render,
        to_image=to_image if with_image else None,
        version="1",
    )


from pathlib import Path  # noqa: E402  (used in _tool)


def test_cli_inspect_exit_1_on_error(tmp_path):
    tool = _tool(tmp_path)
    rc = run(tool, ["inspect", str(tmp_path / "x.py"), "--no-storyboard"])
    assert rc == 1


def test_cli_inspect_writes_storyboard(tmp_path):
    tool = _tool(tmp_path)
    src = tmp_path / "x.py"
    src.write_text("")
    rc = run(tool, ["inspect", str(src), "-o", str(tmp_path / "sb.png")])
    assert rc == 1
    assert (tmp_path / "sb.png").exists()


def test_cli_clean_report_exits_0(tmp_path):
    def inspect(art):
        return Report("R")

    tool = Tool(
        "t", "d", load=lambda p: None, inspect=inspect, render=lambda a, o, d: o, to_image=None
    )
    assert run(tool, ["inspect", str(tmp_path / "x.py"), "--no-storyboard"]) == 0


def test_cli_broken_file_reports_without_traceback(tmp_path, capsys):
    def boom(path):
        raise RuntimeError("nope")

    tool = Tool(
        "t", "d", load=boom, inspect=lambda a: Report("R"), render=lambda a, o, d: o, to_image=None
    )
    rc = run(tool, ["inspect", str(tmp_path / "x.py")])
    assert rc == 2
    assert "RuntimeError: nope" in capsys.readouterr().err


def test_cli_storyboard_honours_top_left_origin(tmp_path):
    from PIL import Image

    def inspect(_):
        return Report("R", problems=[Problem(ERROR, "e", "m", bbox=(10, 10, 40, 40))])

    tool = Tool(
        "t",
        "d",
        load=lambda p: None,
        inspect=inspect,
        render=lambda a, o, d: o,
        to_image=lambda _: Image.new("RGB", (100, 100), "white"),
        origin="top-left",
    )
    src = tmp_path / "x.py"
    src.write_text("")
    out = tmp_path / "sb.png"
    run(tool, ["inspect", str(src), "-o", str(out)])

    img = Image.open(out).convert("RGB")

    def red(pixel):
        return pixel[0] > 200 and pixel[1] < 120 and pixel[2] < 120

    top = sum(1 for x in range(100) for y in range(45) if red(img.getpixel((x, y))))
    bottom = sum(1 for x in range(100) for y in range(55, 100) if red(img.getpixel((x, y))))
    assert top > 0 and bottom == 0


def test_cli_storyboard_failure_does_not_hide_the_report(tmp_path, capsys):
    # shadergx with no GL context computes a report, then cannot draw it; the
    # report must still be printed.
    def inspect(_):
        return Report("R", problems=[Problem(ERROR, "e", "boom")])

    def to_image(_):
        raise RuntimeError("no GL context")

    tool = Tool(
        "t", "d", load=lambda p: None, inspect=inspect, render=lambda a, o, d: o, to_image=to_image
    )
    src = tmp_path / "x.py"
    src.write_text("")
    rc = run(tool, ["inspect", str(src)])
    captured = capsys.readouterr()
    assert rc == 1  # still gated on the report's error
    assert "boom" in captured.out  # the report survived
    assert "storyboard skipped" in captured.err


def test_an_interrupt_in_an_artifact_is_the_shells_code(tmp_path, capsys):
    """In-process so both entry points' handler lines are covered.

    `KeyboardInterrupt` from an artifact (and Ctrl-C) are the same event: 130, with a
    line rather than a traceback. Measured before: a traceback escaped from the entry
    point and the exit code was outside the contract's table.
    """
    from gxcore.cli import run

    artifact = tmp_path / "interrupt.py"
    artifact.write_text("raise KeyboardInterrupt\n", encoding="utf-8")

    class _Tool:
        name = "probe"
        description = "probe"
        version = "0.0.0"
        to_image = None

        @staticmethod
        def load(path):
            from gxcore.loading import load_module

            return load_module(path)

        @staticmethod
        def inspect(artifact):
            raise AssertionError("never inspected")

        @staticmethod
        def render(artifact, out, dpi):
            raise AssertionError("never rendered")

    assert run(_Tool(), ["inspect", str(artifact), "--no-storyboard"]) == 130
    assert "probe: interrupted" in capsys.readouterr().err
