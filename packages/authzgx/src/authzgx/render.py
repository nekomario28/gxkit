"""Map a permission model onto the shared node-link renderer (gxcore.diagram)."""

from __future__ import annotations

from gxcore.diagram import DANGER, DEFAULT, MUTED, START, Edge, Node, node_box, render
from gxcore.diagram import image_size as _image_size
from gxcore.diagram import layout as _layout
from PIL import Image

from .authmodel import AuthModel

__all__ = ["compute_layout", "image_size", "node_box", "render_image"]


def _nodes_edges(model: AuthModel) -> tuple[list[Node], list[Edge]]:
    low = set(model.low)
    sensitive = set(model.sensitive)
    nodes = [
        *[Node(model.pid(p), p, START if p in low else DEFAULT) for p in model.principals],
        *[Node(model.rid(r), r, DEFAULT) for r in model.roles],
        *[Node(model.xid(x), x, DANGER if x in sensitive else MUTED) for x in model.permissions],
    ]
    edges = [
        *[Edge(model.pid(p), model.rid(r)) for p, r in model.assigned],
        *[Edge(model.rid(c), model.rid(p)) for c, p in model.inherits],
        *[Edge(model.rid(r), model.xid(x)) for r, x in model.grants],
    ]
    return nodes, edges


def image_size(model: AuthModel) -> tuple[int, int]:
    return _image_size(len(model.all_nodes()))


def compute_layout(model: AuthModel) -> tuple[dict[str, tuple[float, float]], float]:
    return _layout(model.all_nodes())


def render_image(model: AuthModel) -> Image.Image:
    nodes, edges = _nodes_edges(model)
    return render(nodes, edges)
