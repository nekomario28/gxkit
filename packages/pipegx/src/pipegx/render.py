"""Map a build pipeline onto the shared node-link renderer (gxcore.diagram)."""

from __future__ import annotations

from gxcore.diagram import ACCEPT, DEFAULT, START, Edge, Node, node_box, render
from gxcore.diagram import image_size as _image_size
from gxcore.diagram import layout as _layout
from PIL import Image

from .model import Pipeline

__all__ = ["compute_layout", "image_size", "node_box", "render_image"]


def _nodes_edges(pipeline: Pipeline) -> tuple[list[Node], list[Edge]]:
    goals = set(pipeline.goals)
    nodes: list[Node] = []
    for step in pipeline.steps:
        kind = START if not step.needs else (ACCEPT if goals & set(step.produces) else DEFAULT)
        nodes.append(Node(step.name, step.name, kind))
    edges = [Edge(need, step.name) for step in pipeline.steps for need in step.needs]
    return nodes, edges


def image_size(pipeline: Pipeline) -> tuple[int, int]:
    return _image_size(len(pipeline.steps))


def compute_layout(pipeline: Pipeline) -> tuple[dict[str, tuple[float, float]], float]:
    return _layout(pipeline.names())


def render_image(pipeline: Pipeline) -> Image.Image:
    nodes, edges = _nodes_edges(pipeline)
    return render(nodes, edges)
