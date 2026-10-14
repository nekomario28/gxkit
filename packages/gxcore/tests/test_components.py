"""Tests for the extracted shared components: graph, layout, loading."""

from __future__ import annotations

from gxcore.geometry import canvas_box
from gxcore.graph import (
    can_reach,
    distances,
    find_cycle,
    reachable,
    reverse,
    shortest_path,
    terminals,
    traps,
    unreachable,
    weak_components,
)
from gxcore.layout import TextBox
from gxcore.layout import check as check_layout
from gxcore.loading import load_from_file, load_module, resolve

# --------------------------------------------------------------------------- #
# graph
# --------------------------------------------------------------------------- #


def test_reachable_and_distance():
    g = {"a": ["b"], "b": ["c"], "c": []}
    assert reachable(g, ["a"]) == {"a", "b", "c"}
    assert distances(g, "a") == {"a": 0, "b": 1, "c": 2}


def test_reverse_and_can_reach():
    g = {"a": ["b"], "b": ["c"], "c": []}
    assert reverse(g)["c"] == ["b"]
    assert can_reach(g, ["c"]) == {"a", "b", "c"}


def test_traps_are_reachable_but_cannot_return():
    # a -> b -> c (dead end); a -> d -> goal
    g = {"a": ["b", "d"], "b": ["c"], "c": [], "d": ["goal"], "goal": []}
    assert traps(g, ["a"], ["goal"]) == {"b", "c"}


def test_symmetric_graph_has_no_traps():
    g = {"a": ["b"], "b": ["a", "goal"], "goal": []}
    assert traps(g, ["a"], ["goal"]) == set()


def test_terminals_and_components():
    g = {"a": ["b"], "b": [], "x": ["y"], "y": []}
    assert set(terminals(g, ["a", "b", "x", "y"])) == {"b", "y"}
    comps = [set(c) for c in weak_components(g)]
    assert {"a", "b"} in comps and {"x", "y"} in comps


def test_find_cycle():
    assert find_cycle({"a": ["b"], "b": ["a"]}) is not None
    assert find_cycle({"a": ["b"], "b": ["c"], "c": []}) is None
    assert find_cycle({"a": ["a"]}) == ["a", "a"]


def test_shortest_path():
    g = {"a": ["b"], "b": ["c"], "c": []}
    assert shortest_path(g, "a", "c") == ["a", "b", "c"]
    assert shortest_path(g, "a", "a") == ["a"]
    assert shortest_path(g, "c", "a") is None


def test_unreachable():
    g = {"a": ["b"], "b": [], "x": []}
    assert unreachable(g, ["a"], ["a", "b", "x"]) == {"x"}


def test_canvas_box():
    assert canvas_box(4, 3) == (0.0, 0.0, 4.0, 3.0)


# --------------------------------------------------------------------------- #
# layout
# --------------------------------------------------------------------------- #

CANVAS = (0.0, 0.0, 100.0, 100.0)


def codes(problems):
    return {p.code for p in problems}


def test_small_text():
    items = [TextBox("tick", "Q1", (10, 10, 30, 20), fontsize=6)]
    assert "small-text" in codes(check_layout(items, CANVAS))


def test_clipped_text():
    items = [TextBox("title", "long", (-20, 10, 30, 20), fontsize=12)]
    assert "clipped-text" in codes(check_layout(items, CANVAS))


def test_text_overlap():
    a = TextBox("a", "hello", (10, 10, 50, 30), 12)
    b = TextBox("b", "world", (12, 12, 52, 32), 12)
    assert "text-overlap" in codes(check_layout([a, b], CANVAS))


def test_identical_text_is_not_flagged_as_overlap():
    a = TextBox("a", "same", (10, 10, 50, 30), 12)
    b = TextBox("b", "same", (10, 10, 50, 30), 12)
    assert "text-overlap" not in codes(check_layout([a, b], CANVAS))


def test_clean_layout_is_empty():
    items = [TextBox("a", "hello", (5, 5, 40, 25), 12), TextBox("b", "world", (55, 60, 90, 80), 12)]
    assert check_layout(items, CANVAS) == []


# --------------------------------------------------------------------------- #
# loading
# --------------------------------------------------------------------------- #


def test_load_module_and_resolve(tmp_path):
    f = tmp_path / "thing.py"
    f.write_text("name = 'hi'\ndef build():\n    return 42\n")
    mod = load_module(f)
    assert resolve(mod, attrs=("missing",), builders=("build",)) == 42


def test_load_from_file_uses_attr_first(tmp_path):
    f = tmp_path / "thing.py"
    f.write_text("value = 1\ndef build():\n    return 2\n")
    value, _ = load_from_file(f, attrs=("value",), builders=("build",))
    assert value == 1


def test_load_from_file_custom_error(tmp_path):
    f = tmp_path / "empty.py"
    f.write_text("x = 1\n")
    import pytest

    with pytest.raises(ValueError, match="no gadget found"):
        load_from_file(f, attrs=("gadget",), builders=(), description="gadget")
