"""Prove every docgx check fires on a page that has the fault.

The text-layout checks come from gxcore.layout (shared with chartgx); docgx adds
the document concerns.
"""

from __future__ import annotations

from pathlib import Path

from docgx import Block, Page, inspect_page, load_page
from gxcore import ERROR, INFO, WARN
from gxcore.testing import assert_fires, assert_quiet

GOOD = Page(
    width=1280,
    height=720,
    title="Q3 results",
    blocks=[
        Block("Revenue up 12%.", x=0.08, y=0.24, font_size=32),
        Block("Costs flat.", x=0.08, y=0.46, font_size=28),
    ],
    max_words=60,
    name="good",
)


def test_good_page_has_no_problems():
    assert inspect_page(GOOD).problems == []


def test_long_block_is_clipped():
    page = Page(
        width=800,
        height=400,
        title="t",
        blocks=[Block(" ".join(["word"] * 400), x=0.05, y=0.1, font_size=30)],
        name="x",
    )
    assert_fires(inspect_page(page), "clipped-text", ERROR)


def test_overlapping_blocks():
    page = Page(
        width=800,
        height=400,
        title="t",
        blocks=[
            Block("alpha", x=0.1, y=0.2, font_size=40),
            Block("beta", x=0.1, y=0.2, font_size=40),
        ],
        name="x",
    )
    assert_fires(inspect_page(page), "text-overlap", ERROR)


def test_small_text():
    page = Page(
        width=800,
        height=400,
        title="t",
        blocks=[Block("tiny", x=0.1, y=0.2, font_size=5)],
        name="x",
    )
    assert_fires(inspect_page(page), "small-text", INFO)


def test_no_title():
    page = Page(width=800, height=400, blocks=[Block("body", x=0.1, y=0.2)], name="x")
    assert_fires(inspect_page(page), "no-title", WARN)


def test_too_much_text():
    page = Page(
        width=800,
        height=400,
        title="t",
        max_words=3,
        blocks=[Block("one two three four five", x=0.1, y=0.3)],
        name="x",
    )
    assert_fires(inspect_page(page), "too-much-text", WARN)


def test_reading_order():
    page = Page(
        width=800,
        height=400,
        title="t",
        blocks=[Block("second", x=0.1, y=0.5), Block("first", x=0.1, y=0.2)],
        name="x",
    )
    assert_fires(inspect_page(page), "reading-order", INFO)


def test_empty_page():
    assert_fires(inspect_page(Page(width=800, height=400, name="x")), "empty-page", INFO)


def test_good_page_is_quiet():
    assert_quiet(inspect_page(GOOD), "clipped-text")
    assert_quiet(inspect_page(GOOD), "text-overlap")


def test_examples_load_and_are_diagnosed():
    examples = Path(__file__).resolve().parents[1] / "examples"
    good, _ = load_page(examples / "good_page.py")
    crowded, _ = load_page(examples / "crowded_page.py")
    assert inspect_page(good).errors == 0
    r = inspect_page(crowded)
    assert_fires(r, "clipped-text", ERROR)
    assert_fires(r, "no-title", WARN)
    assert_fires(r, "too-much-text", WARN)
    assert_fires(r, "reading-order", INFO)
