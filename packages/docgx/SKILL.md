---
name: docgx
description: Inspect a page, slide, or single-screen layout for text that overflows the canvas, blocks that overlap each other, text below the readable floor, a missing title, a word count over budget, or blocks declared out of reading order. Declare a title and positioned text blocks as data; get stable codes, exit codes, and an annotated storyboard. Use when generating a slide, poster, one-pager, card, or fixed-size layout from code and you need to prove the text fits and is readable before rendering — especially when an agent is writing the layout. Not for reflowing web pages or for measuring a free-flowing document.
---

# docgx — prove a fixed-size page fits

Part of the `gxkit` family; the review contract is shared with every `*gx` tool.

## Install

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/docgx" docgx --help
uv tool install ./packages/docgx
```

## Write a page

```python
import docgx as d

page = d.Page(
    width=1280,
    height=720,
    title="Q3 results",
    blocks=[
        d.Block("Revenue up 12%.", x=0.08, y=0.24, font_size=32),
        d.Block("Costs flat.", x=0.08, y=0.46, font_size=28),
    ],
    max_words=60,
)
```

Or module-level `TITLE` / `BLOCKS` / `WIDTH` / `HEIGHT` / `MAX_WORDS`. `x`/`y`
are fractions of the page (0..1, top-left origin).

## The loop

1. Write the page as a Python file.
2. `docgx inspect page.py` — size, block/word count, problems with stable
   `code`s, and `<name>.storyboard.png`. **Exit 1 on any error.**
3. Fix and inspect again; the storyboard boxes each offending block.
4. `docgx render page.py -o page.png`.

## Severities

`error` = text is lost or unreadable (`clipped-text`, `text-overflow`, `text-overlap`).
`warn` = missing title or over budget. `info` = small text, reading order, or
empty page.

## What it catches

| code | severity | meaning |
| --- | --- | --- |
| `clipped-text` | error | a block runs off the page |
| `text-overflow` | error | a block runs out of the box it declares (`width`/`height`) |
| `text-overlap` | error | two blocks cover each other |
| `no-title` | warn | the page has no title |
| `too-much-text` | warn | more words than `max_words` allows |
| `small-text` | info | text below the readable floor |
| `reading-order` | info | blocks declared out of top-to-bottom order |
| `empty-page` | info | no content |

The overlap / clipping / small-text checks are `gxcore.layout` — the *same code*
`chartgx` uses on a matplotlib figure, applied to a page. Every check has a test
that proves it fires on a page with the fault and stays quiet on one without.
