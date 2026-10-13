"""A layered module graph that should pass.

`api` (the entry point) depends down through `service` and `domain` to `util`;
no dependency points upward, there are no cycles, and nothing is dead.
"""

import depsgx as d

NAME = "Layered app"

graph = d.ModuleGraph(
    modules=["api", "service", "domain", "util"],
    depends=[
        ("api", "service"),
        ("service", "domain"),
        ("domain", "util"),
    ],
    roots=["api"],
    layers=[["api"], ["service"], ["domain"], ["util"]],
)
