"""Draw a level as a raster the storyboard can annotate.

Coordinates here are top-left origin (raster space), so problems carry
``origin="top-left"`` boxes.
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from .level import GOAL, HAZARD, ITEM, ONEWAY, SPAWN, WALL, Level

CELL = 34
MARGIN = 14

_COLORS = {
    WALL: (42, 46, 58),
    ".": (236, 236, 236),
    " ": (236, 236, 236),
    SPAWN: (86, 200, 120),
    GOAL: (240, 196, 60),
    ITEM: (120, 180, 240),
    HAZARD: (220, 84, 84),
    ">": (206, 208, 224),
    "<": (206, 208, 224),
    "v": (206, 208, 224),
    "^": (206, 208, 224),
}
_GLYPH = {SPAWN: "S", GOAL: "G", ITEM: "X", HAZARD: "!", **{k: k for k in ONEWAY}}
_INK = (24, 24, 28)


def cell_box(r: int, c: int, cell: int = CELL, margin: int = MARGIN) -> tuple[float, float, float, float]:
    x0 = margin + c * cell
    y0 = margin + r * cell
    return (float(x0), float(y0), float(x0 + cell), float(y0 + cell))


def image_size(level: Level, cell: int = CELL, margin: int = MARGIN) -> tuple[int, int]:
    return (margin * 2 + level.width * cell, margin * 2 + level.height * cell)


def render_image(level: Level, cell: int = CELL, margin: int = MARGIN) -> Image.Image:
    img = Image.new("RGB", image_size(level, cell, margin), (24, 26, 34))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=max(12, int(cell * 0.62)))
    except Exception:
        font = ImageFont.load_default()

    for r in range(level.height):
        for c in range(level.width):
            ch = level.at(r, c) or " "
            x0, y0, x1, y1 = cell_box(r, c, cell, margin)
            draw.rectangle((x0, y0, x1, y1),
                           fill=_COLORS.get(ch, (236, 236, 236)),
                           outline=(196, 198, 208) if ch not in (WALL, None) else None)
            glyph = _GLYPH.get(ch)
            if glyph:
                draw.text((x0 + cell * 0.28, y0 + cell * 0.16), glyph, fill=_INK, font=font)
    return img
