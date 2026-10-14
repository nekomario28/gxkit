"""Map an environment declaration onto the shared node-link renderer (gxcore.diagram)."""

from __future__ import annotations

from gxcore.diagram import DANGER, DEFAULT, START, Edge, Node, node_box, render
from gxcore.diagram import image_size as _image_size
from gxcore.diagram import layout as _layout
from PIL import Image

from .model import Environment

__all__ = ["compute_layout", "image_size", "node_box", "render_image"]


def _ids(env: Environment) -> list[str]:
    return [f"v[{i}]" for i in range(len(env.variables))]


def _nodes_edges(env: Environment) -> tuple[list[Node], list[Edge]]:
    nodes = [Node("env", env.name, DEFAULT)]
    for i, variable in enumerate(env.variables):
        kind = DANGER if variable.secret else (START if variable.required else DEFAULT)
        nodes.append(Node(f"v[{i}]", variable.name, kind))
    edges = [Edge("env", f"v[{i}]") for i in range(len(env.variables))]
    return nodes, edges


def image_size(env: Environment) -> tuple[int, int]:
    return _image_size(len(env.variables) + 1)


def compute_layout(env: Environment) -> tuple[dict[str, tuple[float, float]], float]:
    return _layout(["env", *_ids(env)])


def render_image(env: Environment) -> Image.Image:
    nodes, edges = _nodes_edges(env)
    return render(nodes, edges)
