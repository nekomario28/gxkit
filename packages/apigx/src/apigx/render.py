"""Map an API contract onto the shared node-link renderer (gxcore.diagram)."""

from __future__ import annotations

from gxcore.diagram import DEFAULT, START, Edge, Node, node_box, render
from gxcore.diagram import image_size as _image_size
from gxcore.diagram import layout as _layout
from PIL import Image

from .model import API

__all__ = ["compute_layout", "image_size", "node_box", "render_image"]


def _ids(api: API) -> list[str]:
    return [f"ep[{i}]" for i in range(len(api.endpoints))]


def _nodes_edges(api: API) -> tuple[list[Node], list[Edge]]:
    nodes = [Node("base", api.base or "/", START)]
    nodes += [Node(f"ep[{i}]", e.label(), DEFAULT) for i, e in enumerate(api.endpoints)]
    edges = [Edge("base", f"ep[{i}]") for i in range(len(api.endpoints))]
    return nodes, edges


def image_size(api: API) -> tuple[int, int]:
    return _image_size(len(api.endpoints) + 1)


def compute_layout(api: API) -> tuple[dict[str, tuple[float, float]], float]:
    return _layout(["base", *_ids(api)])


def render_image(api: API) -> Image.Image:
    nodes, edges = _nodes_edges(api)
    return render(nodes, edges)
