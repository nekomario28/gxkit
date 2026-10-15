"""depsgx's domain knowledge: is this dependency graph sound?

Two questions a build graph must answer: is it acyclic, and does anything import
*upward* through the layers? Cycles come from `gxcore.graph.find_cycle`; dead
code from reachability out of the entry points.
"""

from __future__ import annotations

from collections import Counter

from gxcore import ERROR, INFO, Problem, Report
from gxcore.graph import (
    cycle_witnesses,
    reverse,
    strongly_connected_components,
    topological_sort,
)

from .model import ModuleGraph
from .render import compute_layout, node_box


def inspect_graph(graph: ModuleGraph, name: str | None = None) -> Report:
    name = name or graph.name
    declared = set(graph.modules)
    edges = graph.edges()
    reverse_edges: dict[str, list[str]] = reverse(edges)

    report = Report(
        name=name,
        subject=f"modules: {len(graph.modules)} modules, {len(graph.depends)} dependencies",
        details=[
            f"{len(graph.modules)} modules, {len(graph.depends)} dependencies",
            "roots: " + (", ".join(graph.roots) or "none"),
        ],
    )
    if graph.layers:
        report.details.append(
            "layers (top→bottom): " + " | ".join(",".join(g) for g in graph.layers)
        )
    order = topological_sort(edges)
    if order is not None and len(order) > 1:
        # ``edges`` points the way a dependency does; a build order is its reverse.
        report.details.append("build order: " + " → ".join(reversed(order)))
    cyclic = [c for c in strongly_connected_components(edges) if len(c) > 1]
    if cyclic:
        report.details.append(
            "cyclic groups: " + " | ".join("{" + ", ".join(sorted(c)) + "}" for c in cyclic)
        )

    out: list[Problem] = []

    for src, dst in graph.depends:
        if declared and src not in declared:
            out.append(
                Problem(
                    ERROR,
                    "dangling-dependency",
                    f"dependency names unknown module {src!r}",
                    target=dst if dst in declared else None,
                )
            )
        if declared and dst not in declared:
            out.append(
                Problem(
                    ERROR,
                    "dangling-dependency",
                    f"dependency names unknown module {dst!r}",
                    target=src if src in declared else None,
                )
            )
        if src == dst:
            out.append(
                Problem(ERROR, "self-dependency", f"module {src!r} depends on itself", target=src)
            )

    # Self-dependencies are their own finding; do not also report them as a cycle.
    acyclic: dict[str, list[str]] = {m: [] for m in graph.modules}
    for src, dst in graph.depends:
        if src != dst:
            acyclic.setdefault(src, []).append(dst)
            acyclic.setdefault(dst, [])
    # One witness per cyclic component, and the component is the finding: a
    # global first-cycle search hides faults in other components, and a rotated
    # witness must not read as new debt.
    for witness, component in cycle_witnesses(acyclic):
        out.append(
            Problem(
                ERROR,
                "cycle",
                f"dependency cycle: {' → '.join(witness)}",
                target=witness[0],
                identity=tuple(component),
            )
        )

    forbidden = {(f[0], f[1]) for f in graph.forbidden}
    for src, dst in graph.depends:
        if (src, dst) in forbidden:
            out.append(
                Problem(
                    ERROR, "forbidden-dependency", f"{src!r} must not depend on {dst!r}", target=src
                )
            )

    for src, dst in graph.depends:
        ls, ld = graph.layer_of(src), graph.layer_of(dst)
        if ls is not None and ld is not None and ld < ls:
            out.append(
                Problem(
                    ERROR,
                    "layer-violation",
                    f"{src!r} (layer {ls}) depends on {dst!r} (layer {ld}) — "
                    "the dependency points upward",
                    target=src,
                )
            )

    for (src, dst), count in Counter(graph.depends).items():
        if count > 1:
            out.append(
                Problem(
                    INFO,
                    "duplicate-dependency",
                    f"{src!r} → {dst!r} is listed {count} times",
                    target=src,
                )
            )

    if graph.roots:
        reachable_set = graph.reachable_from_roots()
        for module in graph.modules:
            if module not in reachable_set:
                out.append(
                    Problem(
                        INFO,
                        "unreachable-module",
                        f"module {module!r} is not reachable from any root — dead code?",
                        target=module,
                    )
                )
        for module in graph.modules:
            if module not in graph.roots and not reverse_edges.get(module):
                out.append(
                    Problem(
                        INFO,
                        "orphan-module",
                        f"nothing depends on {module!r} and it is not a root",
                        target=module,
                    )
                )
    else:
        out.append(
            Problem(INFO, "no-roots", "no root modules declared, so dead code cannot be found")
        )

    positions, r = compute_layout(graph)
    for p in out:
        if p.bbox is None and p.target in positions:
            p.bbox = node_box(positions[p.target], r)

    report.problems = out
    return report
