"""A segmented network that should pass: public reaches only the web tier."""

import netgx as n

NAME = "DMZ"

network = n.Network(
    nodes={
        "internet": "public",
        "lb": "edge",
        "web": "service",
        "admin": "service",
        "db": "data",
    },
    edges=[("internet", "lb"), ("lb", "web"), ("admin", "db")],
    sensitive=["db"],
)
