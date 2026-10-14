"""Draw the evidence.

The picture is the second half of the contract: the text report is for the
agent, the storyboard is for the person (and for a vision-capable model). Each
located problem gets a numbered box, so problem ``[3]`` in the text is box ``3``
in the image.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from PIL import Image

from .model import Problem, sort_key

# Box outline colours by severity.
_COLORS = {
    "error": (231, 76, 60),
    "warn": (243, 156, 18),
    "info": (52, 152, 219),
}


def safe_name(name: str, limit: int = 48) -> str:
    keep = "".join(c if c.isalnum() or c in " -_" else "_" for c in name).strip()
    keep = "_".join(keep.split())
    return keep[:limit].rstrip("_") or "artifact"


def storyboard_path(name: str, out: str | Path | None = None) -> Path:
    if out:
        return Path(out)
    return Path(f"{safe_name(name)}.storyboard.png")


def annotate(
    image: Image.Image,
    problems: Sequence[Problem],
    path: str | Path,
    *,
    origin: str = "bottom-left",
    pad: int | None = None,
) -> Path:
    """Save ``image`` with a numbered box over every problem that has a bbox.

    ``origin`` says how the boxes' y-axis is oriented: ``"bottom-left"`` for
    matplotlib display coordinates (flipped here), ``"top-left"`` for boxes
    already measured in raster space.
    """
    from PIL import ImageDraw, ImageFont

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if image.mode != "RGB":
        image = image.convert("RGB")

    draw = ImageDraw.Draw(image)
    H = image.height
    if pad is None:
        pad = max(3, int(H / 240))
    try:
        font = ImageFont.load_default(size=max(13, int(H / 60)))
    except Exception:  # very old Pillow
        font = ImageFont.load_default()

    flip = origin == "bottom-left"

    # Several problems can share one box (e.g. two faults on the same node).
    # Group them so one rectangle carries every number instead of hiding the
    # earlier boxes under the later ones.
    groups: dict[tuple[float, float, float, float], list[int]] = {}
    representative: dict[tuple[float, float, float, float], Problem] = {}
    for n, p in enumerate(sorted(problems, key=sort_key), start=1):
        if p.bbox is None:
            continue
        key: tuple[float, float, float, float] = (
            float(round(p.bbox[0])),
            float(round(p.bbox[1])),
            float(round(p.bbox[2])),
            float(round(p.bbox[3])),
        )
        groups.setdefault(key, []).append(n)
        representative.setdefault(key, p)

    for key, numbers in groups.items():
        p = representative[key]
        x0, y0, x1, y1 = key
        if flip:
            top, bottom = H - y1, H - y0
        else:
            top, bottom = y0, y1
        box = (x0 - pad, top - pad, x1 + pad, bottom + pad)
        color = _COLORS.get(p.severity, (128, 128, 128))
        draw.rectangle(box, outline=color, width=max(2, int(H / 400)))

        tag = ",".join(str(n) for n in numbers)
        tb = draw.textbbox((0, 0), tag, font=font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        ty = box[1] - th - 6
        if ty < 0:
            ty = box[1] + 2
        tx = max(0.0, box[0])
        draw.rectangle((tx, ty, tx + tw + 8, ty + th + 6), fill=color)
        draw.text((tx + 4, ty + 2), tag, fill=(255, 255, 255), font=font)

    image.save(path)
    return path
