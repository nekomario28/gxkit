"""flowgx's domain knowledge: can this machine actually finish?

A flow chart is a claim about how work proceeds. The same failures recur in
machine-written state machines: a state nothing can reach, a state that dead
ends, a state from which "done" is impossible, and two transitions on the same
event (non-determinism). Reachability, reverse-reachability and cycle detection
come from `gxcore.graph`; the label-layout checks from `gxcore.layout`.
"""

from __future__ import annotations

from collections import defaultdict

from gxcore import ERROR, INFO, Problem, Report
from gxcore.graph import can_reach, find_cycle, reachable
from gxcore.layout import TextBox
from gxcore.layout import check as check_layout

from .machine import Machine
from .render import compute_layout, image_size, node_box


def inspect_machine(machine: Machine, name: str | None = None) -> Report:
    name = name or machine.name
    states = machine.all_states()
    edges = machine.edges()
    declared = set(machine.states)

    report = Report(
        name=name,
        subject=f"machine: {len(states)} states",
        details=[f"{len(states)} states, {len(machine.transitions)} transitions"],
    )
    out: list[Problem] = []

    # Transitions that name a state nobody declared.
    unknown = [s for s in machine.referenced() if declared and s not in declared]
    for s in dict.fromkeys(unknown):
        out.append(Problem(ERROR, "unknown-state",
                           f"state {s!r} is used in a transition but not declared", target=s))

    start = machine.start
    if start is None or start not in states:
        out.append(Problem(ERROR, "no-start",
                           "the machine has no start state (or it is not one of the states)"))

    accept = machine.accepting()
    report.details.append("accepting: " + (", ".join(sorted(accept)) or "none"))
    if not accept:
        out.append(Problem(ERROR, "no-accept",
                           "no accepting/terminal state, so success cannot be defined"))

    reach = reachable(edges, [start]) if start in states else set(states)
    for s in sorted(set(states) - reach):
        out.append(Problem(ERROR, "unreachable-state",
                           f"state {s!r} cannot be reached from {start!r}", target=s))

    if accept:
        safe = can_reach(edges, accept)
        for s in sorted(reach - safe - set(accept)):
            if not edges.get(s):
                out.append(Problem(ERROR, "dead-end",
                                   f"state {s!r} has no outgoing transition and is not "
                                   "accepting — the flow gets stuck", target=s))
            else:
                out.append(Problem(ERROR, "no-exit",
                                   f"state {s!r} cannot reach any accepting state — the flow "
                                   "can never complete from here", target=s))

    # Two transitions from one state on the same event = non-determinism.
    events: dict[str, list[str]] = defaultdict(list)
    for src, ev in machine.events():
        if ev is not None:
            events[src].append(ev)
    for src, evs in events.items():
        for ev in sorted({e for e in evs if evs.count(e) > 1}):
            out.append(Problem(ERROR, "ambiguous-transition",
                               f"state {src!r} has more than one {ev!r} transition — the flow "
                               "is non-deterministic", target=src))

    cycle: list[str] | None = find_cycle(edges)
    if cycle:
        path = " → ".join(cycle)
        report.details.append(f"cycle: {path}")
        out.append(Problem(INFO, "cycle", f"a cycle returns through {path}",
                           target=cycle[0]))

    # Reuse the shared text-layout checks on the node labels.
    positions, r = compute_layout(machine)
    width, height = image_size(machine)
    items = [TextBox("node", s, node_box(positions[s], r), None)
             for s in states if s in positions]
    out.extend(check_layout(items, (0.0, 0.0, float(width), float(height))))

    for p in out:
        if p.bbox is None and p.target in positions:
            p.bbox = node_box(positions[p.target], r)

    report.problems = out
    return report
