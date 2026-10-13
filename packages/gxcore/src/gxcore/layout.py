"""Text-layout checks shared by any tool that renders labelled pixels.

A chart's tick labels and a flow diagram's node labels fail the same three ways:
too small to read, cut off at the canvas edge, or written over each other. The
tool supplies the boxes (it knows its own renderer); this module supplies the
rules and the messages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .geometry import both_covered, clipped
from .model import ERROR, INFO, BBox, Problem


@dataclass
class TextBox:
    role: str
    text: str
    bbox: BBox
    fontsize: float | None = None


def check(
    items: Sequence[TextBox],
    canvas: BBox,
    *,
    target: str | None = None,
    min_fontsize: float = 8.0,
    overlap_fraction: float = 0.35,
    tol: float = 2.0,
) -> list[Problem]:
    out: list[Problem] = []

    for it in items:
        if it.fontsize is not None and it.fontsize < min_fontsize:
            out.append(Problem(
                INFO, "small-text",
                f"{it.role} {it.text!r} is {it.fontsize:g}pt — below the readable floor",
                target=target, label=it.text, bbox=it.bbox,
            ))

    for it in items:
        if clipped(it.bbox, canvas, tol):
            out.append(Problem(
                ERROR, "clipped-text",
                f"{it.role} {it.text!r} is cut off at the canvas edge",
                target=target, label=it.text, bbox=it.bbox,
            ))

    for a in range(len(items)):
        for b in range(a + 1, len(items)):
            x, y = items[a], items[b]
            if x.text.strip() == y.text.strip():
                continue
            if both_covered(x.bbox, y.bbox) > overlap_fraction:
                out.append(Problem(
                    ERROR, "text-overlap",
                    f"{x.role} {x.text!r} and {y.role} {y.text!r} overlap",
                    target=target, label=x.text,
                    bbox=(min(x.bbox[0], y.bbox[0]), min(x.bbox[1], y.bbox[1]),
                          max(x.bbox[2], y.bbox[2]), max(x.bbox[3], y.bbox[3])),
                ))
    return out
