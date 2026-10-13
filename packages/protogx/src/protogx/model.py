"""A protocol state machine: states, the messages that move between them, and
which messages expect a response.

    import protogx as p

    proto = p.Protocol(
        states=["closed", "listen", "syn_sent", "established", "closing"],
        start="closed",
        terminal=["closed"],
        messages=["SYN", "SYN+ACK", "ACK", "FIN"],
        transitions=[
            ("closed", "listen", None),          # internal, no message
            ("listen", "syn_sent", "SYN"),
            ("syn_sent", "established", "SYN+ACK"),
            ("established", "closing", "FIN"),
            ("closing", "closed", "ACK"),
        ],
        requests=["SYN", "FIN"],
        responses={"SYN": "SYN+ACK", "FIN": "ACK"},
    )

Transitions are ``(source, target)`` or ``(source, target, message)``. Declaring
`messages`, `requests` and `responses` is what lets the checks find a message
nothing handles and a request whose reply never arrives.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from gxcore.graph import terminals

Transition = tuple[str, str] | tuple[str, str, str]


@dataclass
class Protocol:
    states: list[str] = field(default_factory=list)
    transitions: list[Transition] = field(default_factory=list)
    start: str | None = None
    terminal: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    requests: list[str] = field(default_factory=list)
    responses: dict[str, str] = field(default_factory=dict)
    name: str = "protocol"

    def all_states(self) -> list[str]:
        seen: list[str] = []
        for s in list(self.states):
            if s not in seen:
                seen.append(s)
        for t in self.transitions:
            for s in (t[0], t[1]):
                if s not in seen:
                    seen.append(s)
        return seen

    def pairs(self) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for t in self.transitions:
            p = (t[0], t[1])
            if p not in out:
                out.append(p)
        return out

    def message_of(self, transition: Transition) -> str | None:
        return transition[2] if len(transition) == 3 else None

    def edges(self) -> dict[str, list[str]]:
        e: dict[str, list[str]] = {s: [] for s in self.all_states()}
        for t in self.transitions:
            e.setdefault(t[0], []).append(t[1])
            e.setdefault(t[1], [])
        return e

    def used_messages(self) -> list[str]:
        return [m for m in (self.message_of(t) for t in self.transitions) if m]

    def accepting(self) -> set[str]:
        if self.terminal:
            return set(self.terminal)
        return set(terminals(self.edges(), self.all_states()))


def _as_protocol(value: object) -> "Protocol | None":
    return value if isinstance(value, Protocol) else None


def load_protocol(path: str | Path) -> tuple[Protocol, object]:
    from gxcore.loading import load_module, resolve

    path = Path(path)
    module = load_module(path)
    proto = resolve(
        module,
        attrs=("protocol", "PROTOCOL", "proto", "machine"),
        builders=("build", "make_protocol", "make"),
        convert=_as_protocol,
    )
    if proto is None:
        transitions = getattr(module, "TRANSITIONS", getattr(module, "transitions", None))
        if transitions is not None:
            proto = Protocol(
                states=list(getattr(module, "STATES", getattr(module, "states", []))),
                transitions=[tuple(t) for t in transitions],
                start=getattr(module, "START", getattr(module, "start", None)),
                terminal=list(getattr(module, "TERMINAL", getattr(module, "terminal", []))),
                messages=list(getattr(module, "MESSAGES", getattr(module, "messages", []))),
                requests=list(getattr(module, "REQUESTS", getattr(module, "requests", []))),
                responses=dict(getattr(module, "RESPONSES", getattr(module, "responses", {}))),
            )
    if proto is None:
        raise ValueError(
            f"{path}: no protocol found — define `protocol` (a Protocol) or "
            "STATES/TRANSITIONS/MESSAGES/REQUESTS/RESPONSES"
        )
    if proto.name == "protocol":
        proto.name = getattr(module, "NAME", path.stem)
    return proto, module


def protocol_from_parts(
    states: list[str] | None = None,
    transitions: list[Transition] | None = None,
    start: str | None = None,
    terminal: list[str] | None = None,
    messages: list[str] | None = None,
    requests: list[str] | None = None,
    responses: dict[str, str] | None = None,
    name: str = "protocol",
) -> Protocol:
    return Protocol(
        states=list(states or []),
        transitions=[tuple(t) for t in (transitions or [])],
        start=start,
        terminal=list(terminal or []),
        messages=list(messages or []),
        requests=list(requests or []),
        responses=dict(responses or {}),
        name=name,
    )
