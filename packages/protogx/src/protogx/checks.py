"""protogx's domain knowledge: can this protocol make progress and finish?

Beyond a state machine's reachability, a protocol has *messages*: one that
nothing handles, or a request whose reply never arrives, is a dead protocol even
when every state is reachable. Reachability, reverse reachability, traps and
cycles all come from `gxcore.graph`.
"""

from __future__ import annotations

from collections import Counter

from gxcore import ERROR, INFO, WARN, Problem, Report
from gxcore.graph import can_reach, find_cycle, reachable

from .model import Protocol
from .render import compute_layout, image_size, node_box


def inspect_protocol(proto: Protocol, name: str | None = None) -> Report:
    name = name or proto.name
    states = proto.all_states()
    declared = set(proto.states)
    edges = proto.edges()
    used = proto.used_messages()

    report = Report(
        name=name,
        subject=f"protocol: {len(states)} states, {len(proto.transitions)} transitions",
        details=[f"{len(states)} states, {len(proto.transitions)} transitions",
                 f"{len(proto.messages)} messages, {len(proto.requests)} requests"],
    )
    out: list[Problem] = []

    if proto.start is None or proto.start not in states:
        out.append(Problem(ERROR, "no-start",
                           "the protocol has no start state (or it is not one of the states)"))

    for t in proto.transitions:
        for s in (t[0], t[1]):
            if declared and s not in declared:
                out.append(Problem(ERROR, "unknown-state",
                                   f"transition names undeclared state {s!r}"))
        message = proto.message_of(t)
        if message and proto.messages and message not in proto.messages:
            out.append(Problem(ERROR, "unknown-message",
                               f"transition uses undeclared message {message!r}", target=t[0]))
    for message in proto.responses.values():
        if proto.messages and message not in proto.messages:
            out.append(Problem(ERROR, "unknown-message",
                               f"a response names undeclared message {message!r}"))

    for message in proto.messages:
        if message not in used:
            out.append(Problem(ERROR, "unhandled-message",
                               f"message {message!r} is declared but no transition handles it"))

    for request in proto.requests:
        reply = proto.responses.get(request)
        if reply and reply not in used:
            out.append(Problem(WARN, "missing-response",
                               f"request {request!r} expects {reply!r}, which no transition handles "
                               "— the request would never be answered"))

    # two transitions from one state on the same message
    seen: dict[tuple[str, str], int] = Counter(
        (t[0], m) for t in proto.transitions if (m := proto.message_of(t))
    )
    for (state, message), count in seen.items():
        if count > 1:
            out.append(Problem(ERROR, "nondeterministic",
                               f"state {state!r} handles {message!r} {count} ways — "
                               "the protocol is non-deterministic", target=state))

    start = proto.start if proto.start in states else (states[0] if states else None)
    reach = reachable(edges, [start]) if start else set()
    for s in sorted(set(states) - reach):
        out.append(Problem(ERROR, "unreachable-state",
                           f"state {s!r} cannot be reached from {start!r}", target=s))

    accepting = proto.accepting()
    if not accepting:
        out.append(Problem(ERROR, "no-terminal",
                           "the protocol has no terminal state, so it can never end"))
    elif start:
        safe = can_reach(edges, accepting)
        for s in sorted(reach - accepting):
            if not edges.get(s):
                out.append(Problem(ERROR, "deadlock",
                                   f"state {s!r} has no outgoing transition and is not terminal — "
                                   "the protocol gets stuck", target=s))
            elif s not in safe:
                out.append(Problem(ERROR, "no-exit",
                                   f"state {s!r} can never reach a terminal state", target=s))

    cycle: list[str] | None = find_cycle(edges)
    if cycle:
        report.details.append("cycle: " + " → ".join(cycle))
        out.append(Problem(INFO, "cycle", f"a cycle returns through {' → '.join(cycle)}",
                           target=cycle[0]))

    positions, r = compute_layout(proto)
    width, height = image_size(proto)
    for p in out:
        if p.bbox is None and p.target in positions:
            p.bbox = node_box(positions[p.target], r)

    report.problems = out
    return report
