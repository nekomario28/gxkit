"""A flat network with faults.

* `web → ghost` names an unknown node            -> dangling-edge
* `internet` reaches the `db` sensitive node      -> public-reaches-sensitive
* `legacy → legacy` allows traffic to itself       -> self-loop
* `internet → web` is listed twice                 -> duplicate-edge
"""

import netgx as n

NAME = "Flat network"

network = n.Network(
    nodes={
        "internet": "public",
        "web": "service",
        "db": "data",
        "legacy": "service",
    },
    edges=[
        ("internet", "web"),
        ("web", "db"),
        ("legacy", "legacy"),
        ("internet", "web"),
        ("web", "ghost"),
    ],
    sensitive=["db"],
)
