"""protogx's domain knowledge: can this protocol make progress and finish?

Beyond a state machine's reachability, a protocol has *messages*: one that
nothing handles, or a request whose reply never arrives, is a dead protocol even
when every state is reachable. Reachability, reverse reachability, traps and
cycles all come from `gxcore.graph`.
"""

from __future__ import annotations

from collections import defaultdict

from gxcore import ERROR, INFO, WARN, Problem, Report
from gxcore.graph import can_reach, cycle_witnesses, reachable

from .model import Protocol
from .render import compute_layout, node_box


def inspect_protocol(proto: Protocol, name: str | None = None) -> Report:
    name = name or proto.name
    states = proto.all_states()
    declared = set(proto.states)
    edges = proto.edges()
    used = proto.used_messages()

    report = Report(
        name=name,
        subject=f"protocol: {len(states)} states, {len(proto.transitions)} transitions",
        details=[
            f"{len(states)} states, {len(proto.transitions)} transitions",
            f"{len(proto.messages)} messages, {len(proto.requests)} requests",
        ],
    )
    out: list[Problem] = []

    if proto.start is None or proto.start not in states:
        out.append(
            Problem(
                ERROR,
                "no-start",
                "the protocol has no start state (or it is not one of the states)",
            )
        )

    for t in proto.transitions:
        for s in (t[0], t[1]):
            if declared and s not in declared:
                out.append(
                    Problem(
                        ERROR,
                        "unknown-state",
                        f"transition names undeclared state {s!r}",
                        identity=(f"transition:{t[0]}->{t[1]}", s),
                    )
                )
        message = proto.message_of(t)
        if message and proto.messages and message not in proto.messages:
            out.append(
                Problem(
                    ERROR,
                    "unknown-message",
                    f"transition uses undeclared message {message!r}",
                    target=t[0],
                    identity=(f"transition:{t[0]}->{t[1]}", message),
                )
            )
    # A terminal state that is not a state resolves to nothing, and the protocol
    # would then be judged against an end condition it does not have.
    for s in proto.terminal:
        if declared and s not in declared:
            out.append(
                Problem(
                    ERROR,
                    "unknown-state",
                    f"terminal state {s!r} is not declared",
                    target=s,
                    identity=("terminal", s),
                )
            )

    for request in proto.requests:
        if proto.messages and request not in proto.messages:
            out.append(
                Problem(
                    ERROR,
                    "unknown-message",
                    f"a request names undeclared message {request!r}",
                    identity=(f"request:{request}", request),
                )
            )
    for request, message in proto.responses.items():
        if proto.messages and message not in proto.messages:
            out.append(
                Problem(
                    ERROR,
                    "unknown-message",
                    f"a response names undeclared message {message!r}",
                    identity=(f"response:{request}", message),
                )
            )

    for message in proto.messages:
        if message not in used:
            # The message is the finding: two unhandled messages are two defects.
            out.append(
                Problem(
                    ERROR,
                    "unhandled-message",
                    f"message {message!r} is declared but no transition handles it",
                    identity=(message,),
                )
            )

    for request in proto.requests:
        reply = proto.responses.get(request)
        if reply and reply not in used:
            out.append(
                Problem(
                    WARN,
                    "missing-response",
                    f"request {request!r} expects {reply!r}, which no transition handles "
                    "— the request would never be answered",
                )
            )

    # two transitions from one state on the same message
    # Distinct targets, not declarations: listing the same transition twice leaves
    # the protocol deterministic, and calling it non-deterministic was measured as a
    # wrong verdict.
    seen: dict[tuple[str, str], set[str]] = defaultdict(set)
    for t in proto.transitions:
        if message := proto.message_of(t):
            seen[(t[0], message)].add(t[1])
    for (state, message), destinations in seen.items():
        if len(destinations) > 1:
            out.append(
                Problem(
                    ERROR,
                    "nondeterministic",
                    f"state {state!r} handles {message!r} {len(destinations)} ways — "
                    "the protocol is non-deterministic",
                    target=state,
                )
            )

    start = proto.start if proto.start in states else (states[0] if states else None)
    reach = reachable(edges, [start]) if start else set()
    for s in sorted(set(states) - reach):
        out.append(
            Problem(
                ERROR,
                "unreachable-state",
                f"state {s!r} cannot be reached from {start!r}",
                target=s,
            )
        )

    accepting = proto.accepting()
    if not accepting:
        out.append(
            Problem(ERROR, "no-terminal", "the protocol has no terminal state, so it can never end")
        )
    elif start:
        safe = can_reach(edges, accepting)
        for s in sorted(reach - accepting):
            if not edges.get(s):
                out.append(
                    Problem(
                        ERROR,
                        "deadlock",
                        f"state {s!r} has no outgoing transition and is not terminal — "
                        "the protocol gets stuck",
                        target=s,
                    )
                )
            elif s not in safe:
                out.append(
                    Problem(
                        ERROR, "no-exit", f"state {s!r} can never reach a terminal state", target=s
                    )
                )

    for witness, component in cycle_witnesses(edges, self_loops=False):
        report.details.append("cycle: " + " → ".join(witness))
        out.append(
            Problem(
                INFO,
                "cycle",
                f"a cycle returns through {' → '.join(witness)}",
                target=witness[0],
                identity=tuple(component),
            )
        )

    positions, r = compute_layout(proto)
    for p in out:
        if p.bbox is None and p.target in positions:
            p.bbox = node_box(positions[p.target], r)

    report.problems = out
    return report
