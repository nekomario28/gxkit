"""Contact sheet: sampled frames in a grid, the storyboard evidence for a clip."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .clip import Video
from .probe import VideoError, sample_frames

CELL_W, CELL_H = 160, 90
COLS = 6
GAP = 8
MARGIN = 12
LABEL_H = 14
BG = (15, 17, 23)


def _rows(n: int) -> int:
    return max(1, math.ceil(n / COLS))


def sheet_size(n: int) -> tuple[int, int]:
    cols = min(COLS, max(1, n))
    width = MARGIN * 2 + cols * CELL_W + (cols - 1) * GAP
    height = MARGIN * 2 + _rows(n) * (CELL_H + LABEL_H) + (_rows(n) - 1) * GAP
    return width, height


def cell_box(i: int, n: int = COLS) -> tuple[float, float, float, float]:
    row, col = divmod(i, COLS)
    x = MARGIN + col * (CELL_W + GAP)
    y = MARGIN + row * (CELL_H + LABEL_H + GAP)
    return (float(x), float(y), float(x + CELL_W), float(y + CELL_H))


def contact_sheet(video: Video) -> Image.Image:
    media = video.resolved_path or Path(video.path)
    frames = None
    try:
        frames = sample_frames(media, video.sample_fps)
    except VideoError:
        frames = None

    try:
        font = ImageFont.load_default(size=12)
    except Exception:
        font = ImageFont.load_default()

    if frames is None or frames.shape[0] == 0:
        img = Image.new("RGB", sheet_size(1), BG)
        ImageDraw.Draw(img).text((MARGIN, MARGIN), "no frames could be decoded",
                                 fill=(200, 80, 80), font=font)
        return img

    n = int(frames.shape[0])
    img = Image.new("RGB", sheet_size(n), BG)
    draw = ImageDraw.Draw(img)
    for i in range(n):
        box = cell_box(i, n)
        frame = Image.fromarray(frames[i]).convert("RGB").resize((CELL_W, CELL_H))
        img.paste(frame, (int(box[0]), int(box[1])))
        draw.text((box[0], box[1] + CELL_H + 1), f"{i}", fill=(150, 156, 168), font=font)
    return img
