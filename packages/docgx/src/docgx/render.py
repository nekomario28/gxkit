"""Render a page with PIL and report each text block's pixel box.

The same functions measure and draw, so the boxes the checks reason about are
exactly the boxes the storyboard outlines. Coordinates are top-left pixels.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .model import Block, Page

MARGIN = 26
INK = (24, 24, 28)
BACKGROUND = (255, 255, 255)


def _font(size: int) -> Any:
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


def _wrap_width(page: Page, block: Block, x: int) -> float:
    """The width this block's text wraps at: its declared column, or the page.

    Measured on a real two-column deck: wrapping every block at the page width
    laid the left column out as a handful of full-width lines, so its height was
    far too small and its box ran across the right column.
    """
    available: float = page.width - x - MARGIN
    if block.width is not None:
        available = min(available, block.width * page.width)
    return max(40.0, available)


def _declared_box(
    page: Page, block: Block, x: int, y: int
) -> tuple[float, float, float, float] | None:
    """The box a block declares it occupies, or None when it declares none.

    A block with neither ``width`` nor ``height`` is measured and drawn exactly as
    before, and no overflow is claimed about a box that was never declared. A
    declared dimension that is missing falls back to the page's own edge, so
    ``width`` alone still says "this text must stay inside this column".
    """
    if block.width is None and block.height is None:
        return None
    right = x + (block.width * page.width if block.width is not None else page.width - MARGIN - x)
    bottom = y + (
        block.height * page.height if block.height is not None else page.height - MARGIN - y
    )
    return (float(x), float(y), float(right), float(bottom))


def _measure(
    draw: ImageDraw.ImageDraw,
    kind: str,
    text: str,
    lines: list[str],
    font: ImageFont.ImageFont,
    x: int,
    y: int,
    size: int,
) -> dict[str, Any]:
    top = float(y)
    cursor = float(y)
    width = 0.0
    for line in lines:
        box = draw.textbbox((x, cursor), line, font=font)
        width = max(width, box[2] - x)
        cursor = max(cursor, box[3])
    return {
        "kind": kind,
        "text": text,
        "lines": lines,
        "font": font,
        "fontsize": size,
        "x": x,
        "y": top,
        "bbox": (float(x), top, float(x + width), cursor),
    }


def block_boxes(page: Page) -> list[dict[str, Any]]:
    """Every text block with its pixel bbox, in draw order."""
    probe = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(probe)
    items: list[dict[str, Any]] = []

    if page.title:
        font = _font(page.title_size)
        lines = _wrap(draw, page.title, font, page.width - 2 * MARGIN)
        title = _measure(draw, "title", page.title, lines, font, MARGIN, MARGIN, page.title_size)
        title["box"] = None
        items.append(title)

    for block in page.blocks:
        font = _font(block.font_size)
        x = int(block.x * page.width)
        y = int(block.y * page.height)
        lines = _wrap(draw, block.text, font, _wrap_width(page, block, x))
        item = _measure(draw, "block", block.text, lines, font, x, y, block.font_size)
        item["box"] = _declared_box(page, block, x, y)
        items.append(item)

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
