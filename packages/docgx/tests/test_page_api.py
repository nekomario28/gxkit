"""The docgx public helpers."""

from __future__ import annotations

from docgx import Block, page_from_parts


def test_page_from_parts_roundtrips():
    page = page_from_parts(
        title="T",
        blocks=[Block("b", x=0.1, y=0.2)],
        width=640,
        height=480,
        max_words=5,
        name="p",
    )
    assert (page.title, page.width, page.height, page.max_words, page.name) == (
        "T",
        640,
        480,
        5,
        "p",
    )
    assert len(page.blocks) == 1


def test_load_page_from_module_level_blocks(tmp_path):
    from docgx import load_page

    src = tmp_path / "p.py"
    src.write_text('TITLE = "T"\nBLOCKS = []\nWIDTH = 640\nHEIGHT = 480\nNAME = "p"\n')
    page, _module = load_page(src)
    assert page.title == "T"
    assert (page.width, page.height) == (640, 480)


def test_block_converter_accepts_a_block_a_dict_and_a_string():
    import pytest
    from docgx.model import _block

    block = Block("x")
    assert _block(block) is block
    assert _block({"text": "x"}).text == "x"
    assert _block("hi").text == "hi"
    with pytest.raises(TypeError):
        _block(42)
