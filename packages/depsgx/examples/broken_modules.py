"""A module graph with several architectural faults.

* api -> service -> domain -> util -> api  is a cycle
* util (bottom layer) imports api (top)     -> layer-violation
* domain -> infra is explicitly banned      -> forbidden-dependency
* legacy -> legacy                          -> self-dependency
* ghost -> util names an undeclared module  -> dangling-dependency
* legacy is unreachable from the roots      -> unreachable-module / orphan-module
"""

import depsgx as d

NAME = "Tangle"

graph = d.ModuleGraph(
    modules=["api", "service", "domain", "infra", "util", "legacy"],
    depends=[
        ("api", "service"),
        ("service", "domain"),
        ("domain", "util"),
        ("domain", "infra"),
        ("util", "api"),  # cycle + upward dependency
        ("legacy", "legacy"),  # self-dependency
        ("ghost", "util"),  # dangling source
    ],
    roots=["api"],
    forbidden=[("domain", "infra")],
    layers=[["api"], ["service"], ["domain"], ["infra"], ["util"]],
)
