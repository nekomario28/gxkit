"""Tests for gxcore.diagram and gxcore.toolkit, which the tools exercise but
the core has no direct tests for."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from gxcore import ERROR, Problem, Report
from gxcore.diagram import ACCEPT, START, Edge, Node, image_size, layout, node_box, render
from gxcore.toolkit import scene_tool


# --------------------------------------------------------------------------- #
# diagram
# --------------------------------------------------------------------------- #

def test_layout_is_deterministic_and_inside_the_canvas():
    ids = ["a", "b", "c", "d"]
    pos1, r1 = layout(ids)
    pos2, r2 = layout(ids)
    assert pos1 == pos2 and r1 == r2
    w, h = image_size(len(ids))
    for x, y in pos1.values():
        assert 0 <= x <= w and 0 <= y <= h


def test_image_size_grows_with_nodes():
    assert image_size(1)[0] < image_size(12)[0]
    assert image_size(0)[0] >= 420


def test_node_box_is_a_square_around_the_point():
    assert node_box((10.0, 20.0), 5.0) == (5.0, 15.0, 15.0, 25.0)


def test_render_draws_all_nodes():
    nodes = [Node("a", "A", START), Node("b", "B"), Node("c", "C", ACCEPT)]
    edges = [Edge("a", "b"), Edge("b", "a"), Edge("b", "b")]  # both directions + self-loop
    img = render(nodes, edges)
    assert isinstance(img, Image.Image)
    assert img.size == image_size(3)


def test_render_ignores_edges_to_unknown_nodes():
    img = render([Node("a")], [Edge("a", "ghost")])
    assert img.size == image_size(1)


# --------------------------------------------------------------------------- #
# toolkit
# --------------------------------------------------------------------------- #

def _make_tool(tmp_path: Path):
    def load(path):
        return {"artifact": True}, None

    def inspect(artifact):
        return Report("R", subject="thing", problems=[Problem(ERROR, "e", "m")])

    def to_image(artifact):
        return Image.new("RGB", (20, 20), "white")

    main, tool = scene_tool(name="t", description="d", load=load, inspect=inspect,
                            to_image=to_image)
    return main, tool


def test_scene_tool_loads_wraps_and_exits_on_error(tmp_path):
    main, tool = _make_tool(tmp_path)
    src = tmp_path / "x.py"
    src.write_text("")
    assert main(["inspect", str(src), "--no-storyboard"]) == 1


def test_scene_tool_writes_a_render(tmp_path):
    main, tool = _make_tool(tmp_path)
    src = tmp_path / "x.py"
    src.write_text("")
    out = tmp_path / "o.png"
    assert tool.render(tool.load(src), out, None) == out
    assert out.exists()


def test_scene_tool_storyboard_defaults_to_top_left(tmp_path):
    main, tool = _make_tool(tmp_path)
    assert tool.origin == "top-left"
