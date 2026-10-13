"""Map a module graph onto the shared node-link renderer (gxcore.diagram)."""

from __future__ import annotations

from gxcore.diagram import DEFAULT, START, Edge, Node
from gxcore.diagram import image_size as _image_size
from gxcore.diagram import layout as _layout
from gxcore.diagram import node_box, render

from .model import ModuleGraph

__all__ = ["render_image", "compute_layout", "image_size", "node_box"]


def _nodes_edges(graph: ModuleGraph) -> tuple[list[Node], list[Edge]]:
    roots = set(graph.roots)
    nodes = [Node(m, m, START if m in roots else DEFAULT) for m in graph.modules]
    edges = [Edge(src, dst) for src, dst in graph.depends]
    return nodes, edges


def image_size(graph: ModuleGraph) -> tuple[int, int]:
    return _image_size(len(graph.modules))


def compute_layout(graph: ModuleGraph) -> tuple[dict[str, tuple[float, float]], float]:
    return _layout(graph.modules)


def render_image(graph: ModuleGraph):
    nodes, edges = _nodes_edges(graph)
    return render(nodes, edges)
