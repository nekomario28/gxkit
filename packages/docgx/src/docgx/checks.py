"""docgx's domain knowledge: does the page fit, and is it readable?

The text-layout checks (too small, clipped, overlapping) come from
`gxcore.layout`; docgx adds the document concerns: a title, a word budget, and
blocks declared in the order a reader sees them.
"""

from __future__ import annotations

from gxcore import INFO, WARN, Problem, Report
from gxcore.layout import TextBox
from gxcore.layout import check as check_layout

from .model import Page
from .render import block_boxes


def inspect_page(page: Page, name: str | None = None) -> Report:
    name = name or page.name
    items = block_boxes(page)
    words = sum(len(b.text.split()) for b in page.blocks)

    report = Report(
        name=name,
        subject=f"page: {page.width}x{page.height}",
        details=[f"{page.width}x{page.height}, {len(page.blocks)} blocks, {words} words"],
    )

    canvas = (0.0, 0.0, float(page.width), float(page.height))
    boxes = [TextBox(it["kind"], it["text"], it["bbox"], it["fontsize"]) for it in items]
    out = check_layout(boxes, canvas)

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
