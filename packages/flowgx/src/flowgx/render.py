"""Map a machine onto the shared node-link renderer (gxcore.diagram)."""

from __future__ import annotations

from gxcore.diagram import ACCEPT, DEFAULT, START, Edge, Node, node_box, render
from gxcore.diagram import image_size as _image_size
from gxcore.diagram import layout as _layout
from PIL import Image

from .machine import Machine

__all__ = ["compute_layout", "image_size", "node_box", "render_image"]


def _nodes_edges(machine: Machine) -> tuple[list[Node], list[Edge]]:
    accept = machine.accepting()
    nodes = [
        Node(s, s, START if s == machine.start else (ACCEPT if s in accept else DEFAULT))
        for s in machine.all_states()
    ]
    edges = [Edge(a, b) for a, b in machine.pairs()]
    return nodes, edges


def image_size(machine: Machine) -> tuple[int, int]:
    return _image_size(len(machine.all_states()))


def compute_layout(machine: Machine) -> tuple[dict[str, tuple[float, float]], float]:
    return _layout(machine.all_states())


def render_image(machine: Machine) -> Image.Image:
    nodes, edges = _nodes_edges(machine)
    return render(nodes, edges)
