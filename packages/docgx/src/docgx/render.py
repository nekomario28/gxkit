"""Render a page with PIL and report each text block's pixel box.

The same functions measure and draw, so the boxes the checks reason about are
exactly the boxes the storyboard outlines. Coordinates are top-left pixels.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .model import Page

MARGIN = 26
INK = (24, 24, 28)
BACKGROUND = (255, 255, 255)


def _font(size: int):
    return ImageFont.load_default(size=max(6, int(size)))


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: Any, max_width: float) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _measure(draw, kind, text, lines, font, x, y, size):
    top = y
    bottom = y
    width = 0
    for line in lines:
        box = draw.textbbox((x, y), line, font=font)
        width = max(width, box[2] - x)
        bottom = max(bottom, box[3])
        y = box[3]
    return {
        "kind": kind,
        "text": text,
        "lines": lines,
        "font": font,
        "fontsize": size,
        "x": x,
        "y": top,
        "bbox": (float(x), float(top), float(x + width), float(bottom)),
    }


def block_boxes(page: Page) -> list[dict]:
    """Every text block with its pixel bbox, in draw order."""
    probe = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(probe)
    items: list[dict] = []

    if page.title:
        font = _font(page.title_size)
        lines = _wrap(draw, page.title, font, page.width - 2 * MARGIN)
        items.append(_measure(draw, "title", page.title, lines, font, MARGIN, MARGIN, page.title_size))

    for block in page.blocks:
        font = _font(block.font_size)
        x = int(block.x * page.width)
        y = int(block.y * page.height)
        lines = _wrap(draw, block.text, font, max(40, page.width - x - MARGIN))
        items.append(_measure(draw, "block", block.text, lines, font, x, y, block.font_size))

    return items


def render_image(page: Page) -> Image.Image:
    img = Image.new("RGB", (page.width, page.height), BACKGROUND)
    draw = ImageDraw.Draw(img)
    for item in block_boxes(page):
        y = item["y"]
        for line in item["lines"]:
            draw.text((item["x"], y), line, fill=INK, font=item["font"])
            box = draw.textbbox((item["x"], y), line, font=item["font"])
            y = box[3]
    return img
