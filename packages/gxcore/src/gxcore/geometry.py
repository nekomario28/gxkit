"""Bounding-box maths the visual tools share.

Coordinates are ``(x0, y0, x1, y1)`` rectangles in a raster's pixel space. The
origin is not fixed here — tools that measure in a bottom-left space (matplotlib
display coordinates) flip at storyboard time; the maths is the same either way.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from .model import BBox


def area(b: BBox) -> float:
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def overlap(a: BBox, b: BBox) -> float:
    """Area of the intersection of two boxes."""
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return max(0.0, w) * max(0.0, h)


def covered(a: BBox, b: BBox) -> float:
    """Fraction of ``a`` that is inside ``b`` (0..1)."""
    if area(a) == 0:
        return 0.0
    return overlap(a, b) / area(a)


def both_covered(a: BBox, b: BBox) -> float:
    """The smaller of the two coverage fractions — 'how much do these collide'."""
    return min(covered(a, b), covered(b, a))


def union(boxes: Iterable[BBox]) -> BBox | None:
    it = iter(boxes)
    try:
        first = next(it)
    except StopIteration:
        return None
    x0, y0, x1, y1 = first
    for b in it:
        x0, y0 = min(x0, b[0]), min(y0, b[1])
        x1, y1 = max(x1, b[2]), max(y1, b[3])
    return (x0, y0, x1, y1)


def clipped(b: BBox, canvas: BBox, tol: float = 2.0) -> list[str]:
    """Edges of ``b`` that fall outside ``canvas`` by more than ``tol``."""
    edges: list[str] = []
    if b[0] < canvas[0] - tol:
        edges.append("left")
    if b[2] > canvas[2] + tol:
        edges.append("right")
    if b[1] < canvas[1] - tol:
        edges.append("bottom")
    if b[3] > canvas[3] + tol:
        edges.append("top")
    return edges


def canvas_box(width: int, height: int) -> BBox:
    return (0.0, 0.0, float(width), float(height))


def intersecting_pairs(
    boxes: Sequence[BBox], min_fraction: float = 0.35
) -> list[tuple[int, int, float]]:
    """Index pairs whose boxes collide by at least ``min_fraction`` of the smaller.

    ``covered(a, b)`` is the fraction of *a* inside *b*, so the fraction of whichever
    box is smaller is the larger of the two directions. Using ``both_covered`` (the
    smaller fraction, i.e. of the *larger* box) inverted the documented rule:
    measured, a small box entirely inside a big one scored 0.01 and was reported as no
    collision at all. The comparison is ``>=`` because the docstring says "at least".
    """
    out: list[tuple[int, int, float]] = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            frac = max(covered(boxes[i], boxes[j]), covered(boxes[j], boxes[i]))
            if frac >= min_fraction:
                out.append((i, j, frac))
    return out
