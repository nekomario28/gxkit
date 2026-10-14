"""The depsgx public helpers."""

from __future__ import annotations

from depsgx import ModuleGraph, modules_from_parts
from depsgx.render import image_size
from gxcore.diagram import image_size as node_image_size


def test_modules_from_parts_roundtrips():
    graph = modules_from_parts(
        modules=["a", "b"], depends=[("a", "b")], roots=["a"], layers=[["a"], ["b"]]
    )
    assert graph.modules == ["a", "b"]
    assert graph.depends == [("a", "b")]
    assert graph.layers == [["a"], ["b"]]


def test_image_size_tracks_the_module_count():
    assert image_size(ModuleGraph(modules=["a", "b", "c"])) == node_image_size(3)


def test_load_graph_from_module_level_depends(tmp_path):
    from depsgx import load_graph

    src = tmp_path / "m.py"
    src.write_text('MODULES = ["a", "b"]\nDEPENDS = [("a", "b")]\nROOTS = ["a"]\nNAME = "m"\n')
    graph, _module = load_graph(src)
    assert graph.modules == ["a", "b"]
    assert graph.depends == [("a", "b")]


def test_reachable_from_roots_without_roots_returns_every_module():
    assert ModuleGraph(modules=["a", "b"]).reachable_from_roots() == {"a", "b"}
