"""A slide is not always one column, and a card has a bottom.

Measured on a real class deck — two columns of text beside a references card.
Before `width`/`height` existed, every block wrapped at the page width, so the
left column was laid out as a handful of full-width lines: its height was far too
small, its box ran across the right column, and the references card, whose text
really ran past the card and onto the strip below, was measured as fitting. Both
facts were invisible to the tool and plain in the rendered image.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from docgx import Block, Page, inspect_page, load_page
from docgx.render import block_boxes
from gxcore import ERROR
from gxcore.loading import InvalidArtifact
from gxcore.testing import assert_fires, assert_quiet

# long enough to wrap several times, and made of spaces so it can wrap at all
LONG = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron"


def _page(block: Block) -> Page:
    return Page(width=1000, height=600, title="t", blocks=[block], name="p")


def _only_block(block: Block) -> dict:
    return block_boxes(_page(block))[-1]


def test_a_declared_width_wraps_the_text_inside_its_column():
    wide = _only_block(Block(LONG, x=0.02, y=0.1, font_size=20))
    narrow = _only_block(Block(LONG, x=0.02, y=0.1, font_size=20, width=0.3))
    assert len(narrow["lines"]) > len(wide["lines"])
    # the ink stays inside the declared column (x + width), not the page
    assert narrow["bbox"][2] <= 0.02 * 1000 + 0.3 * 1000 + 2


def test_columns_side_by_side_do_not_overlap_each_other():
    """Two columns of the same text sit beside each other, not on top of each other.

    Wrapped at the page width (the pre-column behaviour) each block's box spans the
    page, so a page like this reported an overlap that the picture does not show.
    """
    page = Page(
        width=1000,
        height=600,
        title="t",
        blocks=[
            Block(LONG, x=0.02, y=0.2, font_size=20, width=0.44),
            Block(LONG, x=0.52, y=0.2, font_size=20, width=0.44),
        ],
        name="p",
    )
    assert_quiet(inspect_page(page), "text-overlap")


def test_text_overflow_fires_when_the_text_is_taller_than_its_card():
    page = _page(Block(LONG, x=0.02, y=0.1, font_size=20, width=0.3, height=0.05))
    assert_fires(inspect_page(page), "text-overflow", ERROR)


def test_text_overflow_stays_quiet_when_the_text_fits_its_card():
    page = _page(Block(LONG, x=0.02, y=0.1, font_size=20, width=0.3, height=0.9))
    assert_quiet(inspect_page(page), "text-overflow")


def test_a_block_that_declares_no_box_is_not_measured_against_one():
    """No box declared, no overflow claimed — the page edge is the only bound."""
    page = _page(Block(LONG * 6, x=0.02, y=0.1, font_size=20))
    assert_quiet(inspect_page(page), "text-overflow")


def test_a_width_only_box_is_measured_to_the_page_bottom():
    """`width` alone still bounds the text: the missing side is the page's own edge."""
    fits = _page(Block(LONG, x=0.02, y=0.1, font_size=20, width=0.3))
    assert_quiet(inspect_page(fits), "text-overflow")
    over = _page(Block(" ".join([LONG] * 9), x=0.02, y=0.1, font_size=20, width=0.3))
    assert_fires(inspect_page(over), "text-overflow", ERROR)


def test_a_height_only_box_is_measured_to_the_right_margin():
    fits = _page(Block(LONG, x=0.02, y=0.1, font_size=20, height=0.9))
    assert_quiet(inspect_page(fits), "text-overflow")
    over = _page(Block("w" * 200, x=0.02, y=0.1, font_size=20, height=0.9))
    assert_fires(inspect_page(over), "text-overflow", ERROR)


def test_a_word_wider_than_its_column_overflows_it():
    """Nothing can wrap a word that does not fit, so the column is the finding."""
    page = _page(Block("w" * 200, x=0.02, y=0.1, font_size=20, width=0.3))
    assert_fires(inspect_page(page), "text-overflow", ERROR)


def test_the_finding_is_drawn_against_the_declared_box():
    """A finding is a claim about the box the block declared (storyboard evidence)."""
    page = _page(Block(LONG, x=0.1, y=0.2, font_size=20, width=0.4, height=0.05))
    problem = next(p for p in inspect_page(page).problems if p.code == "text-overflow")
    assert problem.bbox is not None
    assert problem.bbox[:2] == (100.0, 120.0)
    assert problem.bbox[3] > 120.0 + 0.05 * 600


def test_the_declared_box_is_the_column_and_the_card():
    item = _only_block(Block("hi", x=0.1, y=0.2, font_size=20, width=0.4, height=0.3))
    assert item["box"] == (100.0, 120.0, 500.0, 300.0)


def test_a_block_that_declares_no_box_carries_none():
    assert _only_block(Block("hi", x=0.1, y=0.2))["box"] is None
    # neither does the title, which declares no box
    assert block_boxes(_page(Block("hi")))[0]["box"] is None


def test_a_declared_width_or_height_that_is_not_a_number_is_refused():
    for field in ("width", "height"):
        with pytest.raises(InvalidArtifact, match=field):
            Block("t", **{field: "wide"})


def test_the_examples_show_a_two_column_page_and_an_overflowing_card():
    examples = Path(__file__).resolve().parents[1] / "examples"
    good, _ = load_page(examples / "two_column_page.py")
    bad, _ = load_page(examples / "overflowing_card_page.py")
    assert inspect_page(good).problems == []
    assert_fires(inspect_page(bad), "text-overflow", ERROR)
