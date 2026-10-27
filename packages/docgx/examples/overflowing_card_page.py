"""A card whose text does not fit it.

* the references card is declared 8% of the page tall while its four wrapped
  lines need more -> text-overflow
* everything else about the page is fine: it is inside the canvas, it does not
  cover another block, and it has a title. The card is the failure, and only a
  declared box can see it.
"""

import docgx as d

NAME = "Overflowing card"

page = d.Page(
    width=1280,
    height=720,
    title="A card the text does not fit",
    blocks=[
        d.Block("Left column", x=0.05, y=0.22, font_size=28, width=0.42),
        d.Block(
            "The body of the left column sits beside the card and is fine.",
            x=0.05,
            y=0.34,
            font_size=22,
            width=0.42,
        ),
        d.Block("References", x=0.53, y=0.34, font_size=14, width=0.42),
        d.Block(
            "7) the first source, with a long address, quoted in full\n"
            "8) the second source, with a long address, quoted in full\n"
            "9) the third source, with a long address, quoted in full\n"
            "10) the fourth source, with a long address, quoted in full\n"
            "11) the fifth source, with a long address, quoted in full",
            x=0.53,
            y=0.40,
            font_size=14,
            width=0.42,
            height=0.08,
        ),
    ],
    max_words=200,
)
