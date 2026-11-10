# docgx

**Inspect a page / slide for overflowing, overlapping or unreadable text.**
Declare a title and positioned text blocks; `docgx inspect` wraps and measures
them exactly as it renders them, then reports text that runs off the page or out
of its card, covers other text, is too small to read, or breaks the page's word
budget.

One of the [`gxkit`](../../README.md) tools, built on [`gxcore`](../gxcore)
(reusing its `layout` checks).

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/docgx" docgx inspect page.py
# local:  uvx --from ../../packages/docgx docgx inspect page.py
```

## Writing a page

```python
import docgx as d

page = d.Page(
    width=1280,
    height=720,
    title="Q3 results",
    blocks=[
        d.Block("Revenue up 12% year over year.", x=0.08, y=0.24, font_size=32),
        d.Block("Costs flat; margin improved.", x=0.08, y=0.44, font_size=28),
    ],
    max_words=60,
)
```

`x`/`y` are fractions of the page (0..1, top-left origin). Or module-level
`TITLE` / `BLOCKS` / `WIDTH` / `HEIGHT` / `MAX_WORDS`.

### Two columns, and a card

A slide is not always one column. `width` and `height` (also fractions of the
page) declare the column, or the card, a block lives in: a block with a `width`
wraps inside it, and a block with a `height` is reported as `text-overflow` when
the text it measured is taller than that box. Both are optional, and a block that
declares neither is measured exactly as before.

```python
page = d.Page(
    width=1280,
    height=720,
    title="Where the water goes",
    blocks=[
        d.Block("What we found", x=0.05, y=0.22, font_size=30, width=0.42),
        d.Block(
            "Crops are the sixth largest in the country", x=0.05, y=0.34, font_size=22, width=0.42
        ),
        d.Block("References", x=0.53, y=0.22, font_size=14, width=0.42, height=0.40),
    ],
)
```

`examples/two_column_page.py` is a page like this that passes;
`examples/overflowing_card_page.py` is the same shape with a card too short for
its text.

## The contract

```
$ docgx inspect crowded_page.py
crowded_page.py: Crowded slide
page: 1280x720
storyboard: Crowded_slide.storyboard.png
  1280x720, 3 blocks, 405 words
inspect: 6 problems (2 errors)
  [1] error -          clipped-text: block 'detail detail detail detail detail detail detail de…' is cut off at the canvas edge
  [2] error -          text-overlap: block 'detail detail detail detail detail detail detail de…' and block 'tiny note' overlap
  [3] warn  -          no-title: the page has no title
  ...
```

- **Exit code 1** when any `error`-severity problem is found.
- `--json` prints the same report machine-readably; `--no-storyboard` skips the
  image; `-o name.png` names it.

## Checks

| code | severity | what it means |
| --- | --- | --- |
| `clipped-text` | error | a block runs off the page |
| `text-overflow` | error | a block runs out of the box it declares (`width`/`height`) |
| `text-overlap` | error | two blocks cover each other |
| `no-title` | warn | the page has no title |
| `too-much-text` | warn | more words than `max_words` allows |
| `small-text` | info | text below the readable floor |
| `reading-order` | info | blocks are declared out of top-to-bottom order |
| `empty-page` | info | the page has no content |

## Why it can be trusted

Every check is proven to fire on a page with the fault and to stay quiet on one
without (`tests/`). The overlap / clipping / small-text checks are the *same*
code `chartgx` uses (`gxcore.layout`), now applied to a different artefact.

MIT licensed.
