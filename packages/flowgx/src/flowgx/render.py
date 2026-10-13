"""Draw a machine as a raster the storyboard can annotate.

A deterministic circular layout: the same machine always produces the same
image, so problem boxes measured during inspection line up with the picture.
Coordinates are top-left origin (raster space).
"""

from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFont

from .machine import Machine

EDGE = (122, 128, 142)
INK = (24, 28, 36)
START_FILL = (206, 228, 250)
ACCEPT_FILL = (250, 226, 172)
NODE_FILL = (238, 240, 246)
ACCEPT_RING = (214, 158, 40)
BACKGROUND = (250, 250, 252)


def image_size(machine: Machine) -> tuple[int, int]:
    n = max(1, len(machine.all_states()))
    side = max(420, int(180 + n * 30))
    return (side, side)


def compute_layout(machine: Machine) -> tuple[dict[str, tuple[float, float]], float]:
    states = machine.all_states()
    n = max(1, len(states))
    w, h = image_size(machine)
    cx, cy = w / 2, h / 2
    margin = max(64.0, min(w, h) * 0.16)
    radius = min(w, h) / 2 - margin
    positions: dict[str, tuple[float, float]] = {}
    for i, s in enumerate(states):
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


def render_image(machine: Machine) -> Image.Image:
    w, h = image_size(machine)
    img = Image.new("RGB", (w, h), BACKGROUND)
    draw = ImageDraw.Draw(img)
    positions, r = compute_layout(machine)
    pairs = machine.pairs()
    pair_set = machine.pair_set()

    # edges first, so nodes sit on top
    for src, dst in pairs:
        if src not in positions or dst not in positions:
            continue
        p0, p1 = positions[src], positions[dst]
        if src == dst:  # self-loop
            x, y = p0
            draw.ellipse((x + r * 0.35, y - r * 1.95, x + r * 1.95, y - r * 0.35),
                         outline=EDGE, width=2)
            _arrowhead(draw, (x + r * 1.2, y - r * 0.5), (0.4, 1.0), EDGE)
            continue
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        dist = math.hypot(dx, dy) or 1
        ux, uy = dx / dist, dy / dist
        px, py = -uy, ux
        off = r * 0.75 if (dst, src) in pair_set else 0.0
        a = (p0[0] + ux * r + px * off, p0[1] + uy * r + py * off)
        b = (p1[0] - ux * r + px * off, p1[1] - uy * r + py * off)
        draw.line((a, b), fill=EDGE, width=2)
        _arrowhead(draw, b, (b[0] - a[0], b[1] - a[1]), EDGE)

    # nodes
    accepting = machine.accepting()
    for s, pos in positions.items():
        box = node_box(pos, r)
        fill = START_FILL if s == machine.start else NODE_FILL
        if s in accepting and s != machine.start:
            fill = ACCEPT_FILL
        draw.ellipse(box, fill=fill, outline=(150, 156, 168), width=2)
        if s in accepting:
            ring = node_box(pos, r - 3)
            draw.ellipse(ring, outline=ACCEPT_RING, width=2)
        font, shown = _fit(draw, s, r * 1.7, r * 0.55)
        tb = draw.textbbox((0, 0), shown, font=font)
        draw.text((pos[0] - (tb[2] - tb[0]) / 2, pos[1] - (tb[3] - tb[1]) / 2 - tb[1]),
                  shown, fill=INK, font=font)
    return img
