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

    # A declared name this tool consumes must resolve. `sensitive` is the list the
    # exposure question is made of, and its fallback makes silence worse than
    # absence: when *none* of the names is a node, `sensitive_nodes()` uses every
    # `data` node instead, so the answer is about a different set without saying so.
    for node in net.sensitive:
        if node not in declared:
            out.append(
                Problem(
                    ERROR,
                    "dangling-reference",
                    f"`sensitive` names {node!r}, which is not a declared node",
                    identity=("dangling-reference", "sensitive", node),
                )
            )

    seen: set[tuple[str, str]] = set()
    for src, dst in net.edges:
        for node in (src, dst):
            if node not in declared:
                out.append(
                    Problem(
                        ERROR,
                        "dangling-edge",
                        f"edge {src} → {dst} names unknown node {node!r}",
                        # The finding is about this edge and endpoint, not about how
                        # many unknown endpoints exist: replacing one endpoint with
                        # another is a new relationship, not an unchanged one.
                        identity=(src, dst, node),
                    )
                )
        if src == dst:
            out.append(
                Problem(
                    WARN,
                    "self-loop",
                    f"{src} allows traffic to itself",
                    target=src,
                    identity=(src, src),
                )
            )
        if (src, dst) in seen:
            out.append(
                Problem(
                    INFO,
                    "duplicate-edge",
                    f"edge {src} → {dst} is listed twice",
                    target=src,
                    identity=(src, dst),
                )
            )
        seen.add((src, dst))

    if not net.nodes:
        # Every other tool reports an empty declaration as information. Saying
        # nothing would let "no problems" stand for an artifact that declares no
        # topology at all.
        out.append(Problem(INFO, "no-nodes", "the network declares no nodes"))

    publics = net.public()
    if net.nodes and not publics:
        out.append(
            Problem(
                INFO, "no-public", "no node is marked 'public' — external reach cannot be judged"
            )
        )

    # Every public entry that reaches a sensitive node is its own exposure route:
    # stopping at the first one hid the second, and the finding was identified by
    # the sensitive node alone, so a baseline read a *changed* route as unchanged
    # debt. Both were measured before this was fixed.
    sensitive_nodes, by_kind = net.sensitive_nodes()
    for sensitive in sensitive_nodes:
        for entry in publics:
            path = shortest_path(graph, entry, sensitive)
            if path:
                because = (
                    " (no `sensitive` list is declared, so a `data` node stands in)"
                    if by_kind
                    else ""
                )
                out.append(
                    Problem(
                        ERROR,
                        "public-reaches-sensitive",
                        f"public {entry!r} can reach sensitive {sensitive!r}"
                        f"{because}: " + " → ".join(path),
                        target=sensitive,
                        label=sensitive,
                        identity=(entry, sensitive),
                    )
                )

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
