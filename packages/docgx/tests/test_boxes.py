"""The reported text boxes must contain the pixels they claim to describe.

The boxes `block_boxes` returns are what the clip/overlap checks reason about and
what the storyboard outlines. If they were computed in the wrong coordinate
space, every layout verdict would be wrong while every check "passed". So the
boxes are held against the actual drawn ink.
"""

from __future__ import annotations

import random

import numpy as np
import pytest
from docgx import Block, Page
from docgx.render import BACKGROUND, block_boxes, render_image

WORDS = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta"]


def _ink_bbox(img) -> tuple[int, int, int, int] | None:
    arr = np.asarray(img)
    mask = np.any(arr != np.array(BACKGROUND, dtype=arr.dtype), axis=-1)
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))


@pytest.mark.parametrize("seed", range(24))
def test_reported_block_box_contains_its_ink(seed):
    rng = random.Random(seed)
    text = " ".join(rng.choice(WORDS) for _ in range(rng.randint(1, 8)))
    block = Block(
        text,
        x=rng.uniform(0.05, 0.55),
        y=rng.uniform(0.05, 0.55),
        font_size=rng.randint(10, 40),
    )
    page = Page(width=900, height=600, blocks=[block], name="p")
    box = block_boxes(page)[0]["bbox"]
    ink = _ink_bbox(render_image(page))
    assert ink is not None, "text was laid out but nothing was drawn"
    assert box[0] - 1 <= ink[0] and box[1] - 1 <= ink[1]
    assert ink[2] <= box[2] + 1 and ink[3] <= box[3] + 1


def test_title_ink_is_inside_the_title_box():
    page = Page(width=900, height=600, title="A heading", blocks=[], name="p")
    title = next(it for it in block_boxes(page) if it["kind"] == "title")
    ink = _ink_bbox(render_image(page))
    assert ink is not None
    b = title["bbox"]
    assert b[0] - 1 <= ink[0] and b[1] - 1 <= ink[1]
    assert ink[2] <= b[2] + 1 and ink[3] <= b[3] + 1


def test_an_empty_page_draws_no_ink():
    assert _ink_bbox(render_image(Page(width=200, height=100, name="p"))) is None
