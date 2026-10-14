"""Draw a directed node-link diagram as a raster the storyboard can annotate.

A deterministic circular layout: the same inputs always produce the same image,
so problem boxes measured during inspection line up with the picture. Used by
`flowgx`, `authzgx` and `depsgx`; a tool maps its own model onto `Node`/`Edge`
and gets the drawing for free. Coordinates are top-left origin.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

DEFAULT = "default"
START = "start"
ACCEPT = "accept"
MUTED = "muted"
DANGER = "danger"

FILL = {
    DEFAULT: (238, 240, 246),
    START: (206, 228, 250),
    ACCEPT: (250, 226, 172),
    MUTED: (232, 232, 236),
    DANGER: (250, 214, 210),
}
RING = {ACCEPT: (214, 158, 40)}
EDGE = (122, 128, 142)
INK = (24, 28, 36)
BACKGROUND = (250, 250, 252)


@dataclass
class Node:
    id: str
    label: str | None = None
    kind: str = DEFAULT

    @property
    def text(self) -> str:
        return self.label or self.id


@dataclass
class Edge:
    src: str
    dst: str
    label: str | None = None


def image_size(count: int) -> tuple[int, int]:
    side = max(420, int(180 + max(1, count) * 30))
    return (side, side)


def layout(ids: Sequence[str]) -> tuple[dict[str, tuple[float, float]], float]:
    n = max(1, len(ids))
    w, h = image_size(n)
    cx, cy = w / 2, h / 2
    margin = max(64.0, min(w, h) * 0.16)
    radius = min(w, h) / 2 - margin
    positions: dict[str, tuple[float, float]] = {}
    for i, s in enumerate(ids):
        angle = -math.pi / 2 + 2 * math.pi * i / n
        positions[s] = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))
    circumference = 2 * math.pi * radius
    r = min(40.0, max(16.0, circumference / (2 * n) * 0.85))
    return positions, r


def node_box(pos: tuple[float, float], r: float) -> tuple[float, float, float, float]:
    x, y = pos
    return (x - r, y - r, x + r, y + r)


def _fit(draw: ImageDraw.ImageDraw, text: str, max_width: float, size: float):
    size = max(8, int(size))
    while size > 8:
        font = ImageFont.load_default(size=size)
        if draw.textlength(text, font=font) <= max_width:
            return font, text
        size -= 1
    font = ImageFont.load_default(size=8)
    shown = text
    while shown and draw.textlength(shown + "…", font=font) > max_width:
        shown = shown[:-1]
    return font, (shown + "…") if shown != text else text


def _arrowhead(draw: ImageDraw.ImageDraw, tip, direction, color):
    ux, uy = direction
    norm = math.hypot(ux, uy) or 1
    ux, uy = ux / norm, uy / norm
    px, py = -uy, ux
    size = 9
    a = (tip[0] - ux * size + px * size * 0.55, tip[1] - uy * size + py * size * 0.55)
    b = (tip[0] - ux * size - px * size * 0.55, tip[1] - uy * size - py * size * 0.55)
    draw.polygon([tip, a, b], fill=color)


def render(nodes: Sequence[Node], edges: Sequence[Edge]) -> Image.Image:
    ids = [n.id for n in nodes]
    by_id = {n.id: n for n in nodes}
    w, h = image_size(len(ids))
    img = Image.new("RGB", (w, h), BACKGROUND)
    draw = ImageDraw.Draw(img)
    positions, r = layout(ids)
    pair_set = {(e.src, e.dst) for e in edges}

    for e in edges:
        if e.src not in positions or e.dst not in positions:
            continue
        p0, p1 = positions[e.src], positions[e.dst]
        if e.src == e.dst:
            x, y = p0
            draw.ellipse((x + r * 0.35, y - r * 1.95, x + r * 1.95, y - r * 0.35),
                         outline=EDGE, width=2)
            _arrowhead(draw, (x + r * 1.2, y - r * 0.5), (0.4, 1.0), EDGE)
            continue
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        dist = math.hypot(dx, dy) or 1
        ux, uy = dx / dist, dy / dist
        px, py = -uy, ux
        off = r * 0.75 if (e.dst, e.src) in pair_set else 0.0
        a = (p0[0] + ux * r + px * off, p0[1] + uy * r + py * off)
        b = (p1[0] - ux * r + px * off, p1[1] - uy * r - py * off)
        draw.line((a, b), fill=EDGE, width=2)
        _arrowhead(draw, b, (b[0] - a[0], b[1] - a[1]), EDGE)

    for nid, pos in positions.items():
        node = by_id[nid]
        fill = FILL.get(node.kind, FILL[DEFAULT])
        box = node_box(pos, r)
        draw.ellipse(box, fill=fill, outline=(150, 156, 168), width=2)
        if node.kind in RING:
            draw.ellipse(node_box(pos, r - 3), outline=RING[node.kind], width=2)
        font, shown = _fit(draw, node.text, r * 1.7, r * 0.55)
        tb = draw.textbbox((0, 0), shown, font=font)
        draw.text((pos[0] - (tb[2] - tb[0]) / 2, pos[1] - (tb[3] - tb[1]) / 2 - tb[1]),
                  shown, fill=INK, font=font)
    return img
