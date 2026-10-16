"""A protocol with several faults.

* RST and FIN are declared but no transition handles them  -> unhandled-message
* SYN expects SYN+ACK, which nothing handles               -> missing-response
* state ``stuck`` has no way out and is not terminal        -> deadlock
* ``established`` can never reach the terminal state        -> no-exit
* state ``orphan`` is never referenced                      -> unreachable-state
* ``established`` handles ACK two ways                      -> nondeterministic
"""

import protogx as p

NAME = "Broken handshake"

protocol = p.Protocol(
    states=["closed", "listen", "established", "stuck", "orphan"],
    start="closed",
    terminal=["closed"],
    messages=["SYN", "ACK", "FIN", "RST", "SYN+ACK"],
    transitions=[
        ("closed", "listen", None),
        ("listen", "established", "SYN"),
        ("established", "stuck", "ACK"),
        ("established", "closed", "ACK"),
    ],
    requests=["SYN"],
    responses={"SYN": "SYN+ACK"},
)
