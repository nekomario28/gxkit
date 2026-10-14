"""A page with several faults.

* a very long block overflows the bottom of the page   -> clipped-text
* a tiny block sits on top of it                        -> text-overlap + small-text
* no title                                              -> no-title
* far more words than the budget allows                 -> too-much-text
* the last block is declared above blocks that precede it -> reading-order
"""

import docgx as d

NAME = "Crowded slide"

page = d.Page(
    width=1280,
    height=720,
    title="",
    blocks=[
        d.Block(" ".join(["detail"] * 400), x=0.08, y=0.10, font_size=30),
        d.Block("tiny note", x=0.08, y=0.10, font_size=5),
        d.Block("The key point", x=0.08, y=0.04, font_size=24),
    ],
    max_words=40,
)
