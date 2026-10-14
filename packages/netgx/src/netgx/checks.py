"""netgx's domain knowledge: is this topology segmented and coherent?

The graph questions (reachability, cycles) come from `gxcore.graph`; the network
question is least-privilege: a `public` node must not reach a sensitive one.
"""

from __future__ import annotations

from gxcore import ERROR, INFO, WARN, Problem, Report
from gxcore.graph import reverse, shortest_path

from .model import Network
from .render import compute_layout, node_box


def inspect_network(net: Network, name: str | None = None) -> Report:
    name = name or net.name
    declared = set(net.nodes)
    graph = net.graph()

    report = Report(
        name=name,
        subject=f"network: {len(net.nodes)} nodes, {len(net.edges)} edges",
        details=[f"{len(net.nodes)} nodes, {len(net.edges)} edges"],
    )
    out: list[Problem] = []

    seen: set[tuple[str, str]] = set()
    for src, dst in net.edges:
        for node in (src, dst):
            if node not in declared:
                out.append(
                    Problem(
                        ERROR, "dangling-edge", f"edge {src} → {dst} names unknown node {node!r}"
                    )
                )
        if src == dst:
            out.append(Problem(WARN, "self-loop", f"{src} allows traffic to itself", target=src))
        if (src, dst) in seen:
            out.append(
                Problem(INFO, "duplicate-edge", f"edge {src} → {dst} is listed twice", target=src)
            )
        seen.add((src, dst))

    publics = net.public()
    if net.nodes and not publics:
        out.append(
            Problem(
                INFO, "no-public", "no node is marked 'public' — external reach cannot be judged"
            )
        )

    for sensitive in net.sensitive_nodes():
        for entry in publics:
            path = shortest_path(graph, entry, sensitive)
            if path:
                out.append(
                    Problem(
                        ERROR,
                        "public-reaches-sensitive",
                        f"public {entry!r} can reach sensitive {sensitive!r}: " + " → ".join(path),
                        target=sensitive,
                        label=sensitive,
                    )
                )
                break

    incoming = reverse(graph)
    for node in net.names():
        if not graph.get(node) and not incoming.get(node):
            out.append(
                Problem(INFO, "isolated-node", f"{node!r} has no traffic in or out", target=node)
            )

    positions, r = compute_layout(net)
    for problem in out:
        if problem.bbox is None and problem.target in positions:
            problem.bbox = node_box(positions[problem.target], r)

    report.problems = out
    return report
