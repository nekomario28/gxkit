"""Map a seed manifest onto the shared node-link renderer (gxcore.diagram)."""

from __future__ import annotations

from gxcore.diagram import DANGER, DEFAULT, START, Edge, Node, node_box, render
from gxcore.diagram import image_size as _image_size
from gxcore.diagram import layout as _layout
from PIL import Image

from .model import SeedSpec

__all__ = ["compute_layout", "image_size", "node_box", "render_image"]


def _ids(spec: SeedSpec) -> list[str]:
    return [f"st[{i}]" for i in range(len(spec.streams))]


def _nodes_edges(spec: SeedSpec) -> tuple[list[Node], list[Edge]]:
    nodes = [Node("seed", "seed", START)]
    for i, stream in enumerate(spec.streams):
        kind = DANGER if stream.seed is None else DEFAULT
        label = f"{stream.name}={stream.seed}"
        nodes.append(Node(f"st[{i}]", label, kind))
    edges = [Edge("seed", f"st[{i}]") for i in range(len(spec.streams))]
    return nodes, edges


def image_size(spec: SeedSpec) -> tuple[int, int]:
    return _image_size(len(spec.streams) + 1)


def compute_layout(spec: SeedSpec) -> tuple[dict[str, tuple[float, float]], float]:
    return _layout(["seed", *_ids(spec)])


def render_image(spec: SeedSpec) -> Image.Image:
    nodes, edges = _nodes_edges(spec)
    return render(nodes, edges)
