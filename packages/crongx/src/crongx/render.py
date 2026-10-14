"""Map a schedule onto the shared node-link renderer (gxcore.diagram)."""

from __future__ import annotations

from gxcore.diagram import DANGER, DEFAULT, Edge, Node, node_box, render
from gxcore.diagram import image_size as _image_size
from gxcore.diagram import layout as _layout
from PIL import Image

from .model import Schedule

__all__ = ["compute_layout", "image_size", "node_box", "render_image"]


def _ids(schedule: Schedule) -> list[str]:
    return [f"r[{i}]" for i in range(len(schedule.runs))]


def _nodes_edges(schedule: Schedule) -> tuple[list[Node], list[Edge]]:
    nodes = [Node("schedule", schedule.name, DEFAULT)]
    for i, run in enumerate(schedule.runs):
        kind = DANGER if run.duration < 0 or run.start < 0 else DEFAULT
        label = f"{run.name}@{run.start:g}+{run.duration:g}"
        nodes.append(Node(f"r[{i}]", label, kind))
    edges = [Edge("schedule", f"r[{i}]") for i in range(len(schedule.runs))]
    return nodes, edges


def image_size(schedule: Schedule) -> tuple[int, int]:
    return _image_size(len(schedule.runs) + 1)


def compute_layout(schedule: Schedule) -> tuple[dict[str, tuple[float, float]], float]:
    return _layout(["schedule", *_ids(schedule)])


def render_image(schedule: Schedule) -> Image.Image:
    nodes, edges = _nodes_edges(schedule)
    return render(nodes, edges)
