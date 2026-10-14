"""Map a schema onto the shared node-link renderer (gxcore.diagram)."""

from __future__ import annotations

from gxcore.diagram import DEFAULT, START, Edge, Node, node_box, render
from gxcore.diagram import image_size as _image_size
from gxcore.diagram import layout as _layout

from .model import Schema

__all__ = ["compute_layout", "image_size", "node_box", "render_image"]


def _nodes_edges(schema: Schema) -> tuple[list[Node], list[Edge]]:
    roots = set(schema.roots)
    nodes = [Node(t, t, START if t in roots else DEFAULT) for t in schema.table_names()]
    edges = [Edge(schema.split(child)[0], schema.split(parent)[0])
             for child, parent in schema.foreign_keys]
    return nodes, edges


def image_size(schema: Schema) -> tuple[int, int]:
    return _image_size(len(schema.tables))


def compute_layout(schema: Schema) -> tuple[dict[str, tuple[float, float]], float]:
    return _layout(schema.table_names())


def render_image(schema: Schema):
    nodes, edges = _nodes_edges(schema)
    return render(nodes, edges)
