"""A two-column slide with two cards.

`width` and `height` are fractions of the page: `width` is the column the text
wraps inside, `height` is the card the text has to fit. Without them every block
wraps at the page width, which is what a two-column slide is not — measured on a
real class deck, the left column was laid out as a handful of full-width lines.
"""

import docgx as d

NAME = "Two columns"

page = d.Page(
    width=1280,
    height=720,
    title="Where the water goes",
    blocks=[
        # top-to-bottom: the two headings on one line, then the bodies
        d.Block("What we found", x=0.05, y=0.22, font_size=30, width=0.42),
        d.Block("What we propose", x=0.53, y=0.22, font_size=30, width=0.42),
        d.Block(
            "Crops are the sixth largest in the country, and the number of",
            x=0.05,
            y=0.34,
            font_size=22,
            width=0.42,
        ),
        d.Block(
            "Pay the farmers for the water their flooded fields put back",
            x=0.53,
            y=0.34,
            font_size=22,
            width=0.42,
            height=0.30,
        ),
        d.Block(
            "farmers fell by two fifths in fifteen years.",
            x=0.05,
            y=0.46,
            font_size=22,
            width=0.42,
        ),
        d.Block(
            "into the aquifer the factories draw from.",
            x=0.53,
            y=0.46,
            font_size=22,
            width=0.42,
        ),
    ],
    max_words=200,
)
