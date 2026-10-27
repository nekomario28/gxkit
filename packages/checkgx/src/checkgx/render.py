"""Map a check registry onto the shared renderer: one node per check, declared -> evaluated."""

from __future__ import annotations

from gxcore.diagram import DEFAULT, START, Edge, Node, render
from PIL import Image

from .model import Registry

__all__ = ["render_image"]


def _nodes_edges(registry: Registry) -> tuple[list[Node], list[Edge]]:
    names = list(dict.fromkeys([*registry.checks, *registry.evaluated, *registry.metadata]))
    # A declared check is a start node; one the runner reads but nobody declared is a dangling target.
    nodes = [Node(name, name, START if name in registry.checks else DEFAULT) for name in names]
    declared = set(registry.checks)
    edges = [
        Edge("evaluated", name) for name in names if name in declared and name in registry.evaluated
    ]
    return nodes, edges


def render_image(registry: Registry) -> Image.Image:
    nodes, edges = _nodes_edges(registry)
    return render(nodes, edges)
