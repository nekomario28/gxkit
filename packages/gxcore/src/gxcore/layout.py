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

    for a in range(len(items)):
        for b in range(a + 1, len(items)):
            x, y = items[a], items[b]
            if x.text.strip() == y.text.strip():
                continue
            # Either box substantially inside the other is a collision — a small
            # label on top of a big block counts.
            if (
                covered(x.bbox, y.bbox) > overlap_fraction
                or covered(y.bbox, x.bbox) > overlap_fraction
            ):
                out.append(
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
                    )
                )
    return out
