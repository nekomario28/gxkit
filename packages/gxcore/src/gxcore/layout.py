"""Text-layout checks shared by any tool that renders labelled pixels.

A chart's tick labels and a page's text blocks fail the same three ways: too
small to read, cut off at the surface edge, or written over each other. The tool
supplies the boxes (it knows its own renderer); this module supplies the rules
and the messages.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .geometry import clipped, covered
from .model import ERROR, INFO, BBox, Problem


@dataclass
class TextBox:
    role: str
    text: str
    bbox: BBox
    fontsize: float | None = None


def _short(text: str, limit: int = 52) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def check(
    items: Sequence[TextBox],
    canvas: BBox,
    *,
    target: str | None = None,
    min_fontsize: float = 8.0,
    overlap_fraction: float = 0.35,
    tol: float = 2.0,
    surface: str = "canvas",
) -> list[Problem]:
    out: list[Problem] = []

    for it in items:
        if it.fontsize is not None and it.fontsize < min_fontsize:
            out.append(
                Problem(
                    INFO,
                    "small-text",
                    f"{it.role} {_short(it.text)!r} is {it.fontsize:g}pt — below the readable floor",
                    target=target,
                    label=_short(it.text),
                    bbox=it.bbox,
                )
            )

    for it in items:
        if clipped(it.bbox, canvas, tol):
            out.append(
                Problem(
                    ERROR,
                    "clipped-text",
                    f"{it.role} {_short(it.text)!r} is cut off at the {surface} edge",
                    target=target,
                    label=_short(it.text),
                    bbox=it.bbox,
                )
            )

    # Only boxes whose rectangles *intersect* can be collisions, so the pairs are
    # enumerated by a sweep over x plus a y-bucket, instead of by every pair. Measured:
    # 4 000 boxes laid out in a ring took 33 s in the double loop (16 million `covered`
    # calls) and found nothing at all.
    #
    # Exactness: a collision needs a non-empty intersection, so the two boxes share an
    # x-range *and* a y point — and two boxes sharing a y point share the bucket that
    # point falls in, whatever the bucket size is. Bucketing can therefore only narrow
    # the candidates. A bucket is sized to the middle box, so the ring case (overlapping
    # x, disjoint y) stays near-linear.
    # A grid, not a sweep: a collision needs a non-empty intersection, so the two
    # boxes share an x-range *and* a y point — and two boxes sharing a point share the
    # cell that point falls in, whatever the cell size is. Bucketing can therefore only
    # narrow the candidates, never miss one. Measured: 4 000 boxes in a ring took 33 s in
    # the old double loop (16 million `covered` calls) and found nothing.
    heights = sorted(item.bbox[3] - item.bbox[1] for item in items)
    widths = sorted(item.bbox[2] - item.bbox[0] for item in items)
    if not heights:  # nothing to compare
        return out
    cell_w = max(1.0, widths[len(widths) // 2])
    cell_h = max(1.0, heights[len(heights) // 2])
    buckets: dict[tuple[int, int], list[int]] = {}
    seen: set[tuple[int, int]] = set()
    found: list[tuple[int, int, Problem]] = []
    #: A box covering more cells than this (one huge block among many small ones) would
    #: cost more in candidate collection than it saves, so it falls back to the old
    #: candidate set — every box seen so far.
    cell_budget = 64
    oversized: list[int] = []
    for index, item in enumerate(items):
        x0, y0, x1, y1 = item.bbox
        low_x, high_x = int(x0 // cell_w), int(x1 // cell_w)
        low_y, high_y = int(y0 // cell_h), int(y1 // cell_h)
        covering = (high_x - low_x + 1) * (high_y - low_y + 1)
        if covering > cell_budget:
            # A box that covers many cells is kept *outside* the grid and offered to
            # every later box: measured, leaving it out of the cells entirely lost real
            # collisions (the docgx page's own example, which the transcript pins).
            candidates = list(range(index))
            oversized.append(index)
        else:
            candidates = list(oversized)
            for bx in range(low_x, high_x + 1):
                for by in range(low_y, high_y + 1):
                    candidates.extend(buckets.get((bx, by), ()))
                    buckets.setdefault((bx, by), []).append(index)
        for other in candidates:
            a, b = sorted((index, other))
            if (a, b) in seen:
                continue  # one pair can share more than one cell
            seen.add((a, b))
            x, y = items[a], items[b]
            if x.bbox[3] <= y.bbox[1] or y.bbox[3] <= x.bbox[1]:
                continue
            # The *same* text in the *same* place is one label read twice, not a
            # collision. Keying on the text alone silently dropped a real one:
            # measured, two boxes both called "same" at different positions (0.72 of
            # one inside the other) were accepted.
            if x.text.strip() == y.text.strip() and x.bbox == y.bbox:
                continue
            # One owner for the rule: either box substantially inside the other is a
            # collision — a small label on top of a big block counts (the fraction is
            # of the smaller box, which `intersecting_pairs` documents).
            if max(covered(x.bbox, y.bbox), covered(y.bbox, x.bbox)) >= overlap_fraction:
                found.append(
                    (
                        a,
                        b,
                        Problem(
                            ERROR,
                            "text-overlap",
                            f"{x.role} {_short(x.text)!r} and {y.role} {_short(y.text)!r} overlap",
                            target=target,
                            label=_short(x.text),
                            bbox=(
                                min(x.bbox[0], y.bbox[0]),
                                min(x.bbox[1], y.bbox[1]),
                                max(x.bbox[2], y.bbox[2]),
                                max(x.bbox[3], y.bbox[3]),
                            ),
                        ),
                    )
                )
    # The sweep visits pairs in a different order than the index loop did, so they are
    # reported by index — the order every transcript and baseline was written against.
    out.extend(problem for _a, _b, problem in sorted(found, key=lambda item: (item[0], item[1])))
    return out
