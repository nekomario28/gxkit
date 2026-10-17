"""A page (or slide): a title and positioned text blocks.

    import docgx as d

    page = d.Page(
        width=1280, height=720,
        title="Q3 results",
        blocks=[
            d.Block("Revenue up 12% year over year.", x=0.08, y=0.24, font_size=30),
            d.Block("Costs flat; margin improved.", x=0.08, y=0.42, font_size=26),
        ],
        max_words=60,
    )

``x``/``y`` are fractions of the page (0..1, top-left origin). The renderer wraps
text to the page width, so a long block can still overflow the bottom — which is
what `docgx` catches.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from gxcore.loading import (
    InvalidArtifact,
    convert_items,
    convert_number,
    validate_names,
    validate_number,
)


@dataclass
class Block:
    text: str
    x: float = 0.08
    y: float = 0.25
    font_size: int = 28

    def __post_init__(self) -> None:
        validate_names([self.text], field="text")
        validate_number(self.x, field="x")
        validate_number(self.y, field="y")
        validate_number(self.font_size, field="font_size", integer=True)


@dataclass
class Page:
    width: int = 1280
    height: int = 720
    title: str = ""
    blocks: list[Block] = field(default_factory=list)
    title_size: int = 44
    max_words: int = 0
    name: str = "page"

    def __post_init__(self) -> None:
        validate_number(self.width, field="width", integer=True)
        validate_number(self.height, field="height", integer=True)
        validate_number(self.title_size, field="title_size", integer=True)
        validate_number(self.max_words, field="max_words", integer=True)
        for index, block in enumerate(self.blocks):
            if not isinstance(block, Block):
                raise InvalidArtifact(
                    f"blocks[{index}]: expected a Block, not {type(block).__name__}"
                )


def _as_page(value: object) -> Page | None:
    return value if isinstance(value, Page) else None


def _block(value: object) -> Block:
    if isinstance(value, Block):
        return value
    if isinstance(value, dict):
        return Block(**value)
    if isinstance(value, str):
        return Block(value)
    raise TypeError(f"cannot make a Block from {value!r}")


def load_page(path: str | Path) -> tuple[Page, object]:
    from gxcore.loading import load_module, resolve

    path = Path(path)
    module = load_module(path)
    page = resolve(
        module,
        attrs=("page", "PAGE", "slide", "deck"),
        builders=("build", "make_page", "make"),
        convert=_as_page,
    )
    if page is None:
        blocks = getattr(module, "BLOCKS", getattr(module, "blocks", None))
        if (
            blocks is not None
            or getattr(module, "TITLE", getattr(module, "title", None)) is not None
        ):
            page = Page(
                width=_int(getattr(module, "WIDTH", getattr(module, "width", 1280)), "WIDTH"),
                height=_int(getattr(module, "HEIGHT", getattr(module, "height", 720)), "HEIGHT"),
                title=str(getattr(module, "TITLE", getattr(module, "title", ""))),
                # `BLOCKS = "hi"` used to become one block per character, and a block
                # with a mistyped key raised a `TypeError` naming no field or index.
                blocks=convert_items(blocks or [], _block, field="BLOCKS"),
                title_size=_int(getattr(module, "TITLE_SIZE", 44), "TITLE_SIZE"),
                max_words=_int(getattr(module, "MAX_WORDS", 0), "MAX_WORDS"),
            )
    if page is None:
        raise ValueError(f"{path}: no page found — define `page` (a Page) or TITLE/BLOCKS")
    if page.name == "page":
        page.name = getattr(module, "NAME", path.stem)
    return page, module


def _int(value: object, field: str) -> int:
    """A declared whole number, or a located refusal (`WIDTH = "wide"` used to raise)."""
    return int(convert_number(value, field=field, integer=True))


def page_from_parts(
    title: str = "",
    blocks: list[Block] | None = None,
    width: int = 1280,
    height: int = 720,
    max_words: int = 0,
    name: str = "page",
) -> Page:
    return Page(
        width=width,
        height=height,
        title=title,
        blocks=list(blocks or []),
        max_words=max_words,
        name=name,
    )
