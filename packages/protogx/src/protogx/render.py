"""Map a protocol onto the shared node-link renderer (gxcore.diagram)."""

from __future__ import annotations

from gxcore.diagram import ACCEPT, DEFAULT, START, Edge, Node
from gxcore.diagram import image_size as _image_size
from gxcore.diagram import layout as _layout
from gxcore.diagram import node_box, render

from .model import Protocol

__all__ = ["render_image", "compute_layout", "image_size", "node_box"]


def _nodes_edges(proto: Protocol) -> tuple[list[Node], list[Edge]]:
    accepting = proto.accepting()
    nodes = [
        Node(s, s, START if s == proto.start else (ACCEPT if s in accepting else DEFAULT))
        for s in proto.all_states()
    ]
    edges = [Edge(src, dst) for src, dst in proto.pairs()]
    return nodes, edges


def image_size(proto: Protocol) -> tuple[int, int]:
    return _image_size(len(proto.all_states()))


def compute_layout(proto: Protocol) -> tuple[dict[str, tuple[float, float]], float]:
    return _layout(proto.all_states())


def render_image(proto: Protocol):
    nodes, edges = _nodes_edges(proto)
    return render(nodes, edges)
