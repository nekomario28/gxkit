"""Map a network topology onto the shared node-link renderer (gxcore.diagram)."""

from __future__ import annotations

from gxcore.diagram import ACCEPT, DANGER, DEFAULT, MUTED, START, Edge, Node, node_box, render
from gxcore.diagram import image_size as _image_size
from gxcore.diagram import layout as _layout
from PIL import Image

from .model import Network

__all__ = ["compute_layout", "image_size", "node_box", "render_image"]

_KIND = {"public": START, "edge": ACCEPT, "service": DEFAULT, "data": DANGER}


def _nodes_edges(net: Network) -> tuple[list[Node], list[Edge]]:
    nodes = [Node(name, name, _KIND.get(kind, MUTED)) for name, kind in net.nodes.items()]
    edges = [Edge(src, dst) for src, dst in net.edges]
    return nodes, edges


def image_size(net: Network) -> tuple[int, int]:
    return _image_size(len(net.nodes))


def compute_layout(net: Network) -> tuple[dict[str, tuple[float, float]], float]:
    return _layout(net.names())


def render_image(net: Network) -> Image.Image:
    nodes, edges = _nodes_edges(net)
    return render(nodes, edges)
