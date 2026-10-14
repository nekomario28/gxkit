"""A page that should pass: text fits, blocks do not overlap, there is a title."""

import docgx as d

NAME = "Q3 results"

page = d.Page(
    width=1280,
    height=720,
    title="Q3 results",
    blocks=[
        d.Block(
            "Revenue up 12% year over year, driven by enterprise.", x=0.08, y=0.24, font_size=32
        ),
        d.Block("Costs flat; gross margin improved to 41%.", x=0.08, y=0.44, font_size=28),
        d.Block("Outlook: cautious for Q4.", x=0.08, y=0.62, font_size=28),
    ],
    max_words=60,
)
