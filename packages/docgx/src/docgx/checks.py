"""docgx's domain knowledge: does the page fit, and is it readable?

The text-layout checks (too small, clipped, overlapping) come from
`gxcore.layout`; docgx adds the document concerns: a title, a word budget, a
block that outgrows the column or card it declares, and blocks declared in the
order a reader sees them.
"""

from __future__ import annotations

from gxcore import ERROR, INFO, WARN, Problem, Report
from gxcore.layout import TextBox
from gxcore.layout import check as check_layout

from .model import Page
from .render import block_boxes

# px: a measured box may round a pixel or two past the box that was declared.
BOX_TOLERANCE = 2.0


def inspect_page(page: Page, name: str | None = None) -> Report:
    name = name or page.name
    items = block_boxes(page)
    # "N words on the page": the title is on the page. Measured: a 100-word title
    # against a 10-word budget passed, because only the blocks were counted.
    words = len(page.title.split()) + sum(len(b.text.split()) for b in page.blocks)

    report = Report(
        name=name,
        subject=f"page: {page.width}x{page.height}",
        details=[f"{page.width}x{page.height}, {len(page.blocks)} blocks, {words} words"],
    )

    canvas = (0.0, 0.0, float(page.width), float(page.height))
    boxes = [TextBox(it["kind"], it["text"], it["bbox"], it["fontsize"]) for it in items]
    out = check_layout(boxes, canvas)

    # A block that declares a box is checked against that box. `clipped-text`
    # (gxcore.layout) is the canvas edge; this is the card the text was meant to
    # sit in — the failure the canvas edge cannot see, because the card is inside it.
    for item in items:
        box = item.get("box")
        if box is None:
            continue
        bbox = item["bbox"]
        over = max(bbox[2] - box[2], bbox[3] - box[3])
        if over > BOX_TOLERANCE:
            out.append(
                Problem(
                    ERROR,
                    "text-overflow",
                    f"block {item['text']!r} is {over:.0f}px out of the box it declares",
                    label=item["text"],
                    bbox=(box[0], box[1], max(bbox[2], box[2]), max(bbox[3], box[3])),
                )
            )

    if not page.title.strip():
        out.append(Problem(WARN, "no-title", "the page has no title"))

    if not page.blocks and not page.title.strip():
        out.append(Problem(INFO, "empty-page", "the page has no content"))

    if page.max_words and words > page.max_words:
        out.append(
            Problem(WARN, "too-much-text", f"{words} words on the page (limit {page.max_words})")
        )

    ys = [b.y for b in page.blocks]
    if ys != sorted(ys):
        out.append(Problem(INFO, "reading-order", "blocks are declared out of top-to-bottom order"))

    report.problems = out
    return report
