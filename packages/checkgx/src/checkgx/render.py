"""Map a check registry onto the shared renderer: one node per check, declared -> evaluated."""

from __future__ import annotations

from gxcore.diagram import DEFAULT, START, Edge, Node, render
from gxcore.diagram import image_size as _image_size
from gxcore.diagram import layout as _layout
from PIL import Image

from .model import Registry

__all__ = ["compute_layout", "image_size", "render_image"]


def _nodes_edges(registry: Registry) -> tuple[list[Node], list[Edge]]:
    names = list(dict.fromkeys([*registry.checks, *registry.evaluated, *registry.metadata]))
    # A declared check is a start node; one the runner reads but nobody declared is a dangling target.
    nodes = [
        Node(name, name, START if name in registry.checks else DEFAULT) for name in names
    ]
    declared = set(registry.checks)
    edges = [Edge("evaluated", name) for name in names if name in declared and name in registry.evaluated]
    return nodes, edges


def image_size(registry: Registry) -> tuple[int, int]:
    return _image_size(len(_nodes_edges(registry)[0]))


def compute_layout(registry: Registry) -> tuple[dict[str, tuple[float, float]], float]:
    nodes, _ = _nodes_edges(registry)
    ids = [node.id for node in nodes]
    positions, _ = _layout(ids)
    return positions, float(image_size(registry)[1])


def render_image(registry: Registry) -> Image.Image:
    nodes, edges = _nodes_edges(registry)
    return render(nodes, edges)
