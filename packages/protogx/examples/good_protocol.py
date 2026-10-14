"""A handshake that should pass.

Every state is reachable, the terminal state is reachable from everywhere, every
declared message is handled, and every request's reply is handled too.
"""

import protogx as p

NAME = "Handshake"

protocol = p.Protocol(
    states=["closed", "listen", "syn_sent", "established", "closing"],
    start="closed",
    terminal=["closed"],
    messages=["SYN", "SYN+ACK", "ACK", "FIN"],
    transitions=[
        ("closed", "listen", None),  # internal
        ("listen", "syn_sent", "SYN"),
        ("syn_sent", "established", "SYN+ACK"),
        ("established", "closing", "FIN"),
        ("closing", "closed", "ACK"),
    ],
    requests=["SYN", "FIN"],
    responses={"SYN": "SYN+ACK", "FIN": "ACK"},
)
