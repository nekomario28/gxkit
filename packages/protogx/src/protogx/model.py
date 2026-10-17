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
from gxcore.loading import (
    InvalidArtifact,
    _name,
    convert_items,
    convert_mapping,
    convert_names,
    validate_mapping,
    validate_names,
)

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
        """Every state, first occurrence first, without scanning for duplicates.

        The membership test is a set: a *list* test is a scan, and this is called once
        per inspection over every state and transition — measured, 8 000 states spent
        1.6 s of a 2.0 s inspection inside three of these methods.
        """
        seen: list[str] = []
        known: set[str] = set()
        for s in list(self.states):
            if s not in known:
                known.add(s)
                seen.append(s)
        for t in self.transitions:
            for s in (t[0], t[1]):
                if s not in known:
                    known.add(s)
                    seen.append(s)
        return seen

    def pairs(self) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        known: set[tuple[str, str]] = set()
        for t in self.transitions:
            p = (t[0], t[1])
            if p not in known:
                known.add(p)
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

    def __post_init__(self) -> None:
        validate_names(self.states, field="states")
        validate_names(self.terminal, field="terminal")
        validate_names(self.messages, field="messages")
        validate_names(self.requests, field="requests")
        # The third element is the message, and `None` is a transition with no message
        # (`message_of` documents that), so only the names are checked.
        for index, transition in enumerate(self.transitions):
            if not isinstance(transition, (list, tuple)) or len(transition) not in (2, 3):
                raise InvalidArtifact(
                    f"transitions[{index}]: expected 2 or 3 names, not {transition!r}"
                )
            validate_names(list(transition[:2]), field=f"transitions[{index}]")
            if len(transition) == 3 and transition[2] is not None:
                validate_names([transition[2]], field=f"transitions[{index}][2]")
        validate_mapping(self.responses, field="responses")
        if self.start is not None:
            validate_names([self.start], field="start")


def _as_protocol(value: object) -> Protocol | None:
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
                states=convert_names(
                    getattr(module, "STATES", getattr(module, "states", [])), field="STATES"
                ),
                transitions=[
                    _transition(t, index)
                    for index, t in enumerate(
                        convert_items(transitions, lambda value: value, field="TRANSITIONS")
                    )
                ],
                start=getattr(module, "START", getattr(module, "start", None)),
                terminal=convert_names(
                    getattr(module, "TERMINAL", getattr(module, "terminal", [])), field="TERMINAL"
                ),
                messages=convert_names(
                    getattr(module, "MESSAGES", getattr(module, "messages", [])), field="MESSAGES"
                ),
                requests=convert_names(
                    getattr(module, "REQUESTS", getattr(module, "requests", [])), field="REQUESTS"
                ),
                responses=convert_mapping(
                    getattr(module, "RESPONSES", getattr(module, "responses", {})),
                    field="RESPONSES",
                ),
            )
    if proto is None:
        raise ValueError(
            f"{path}: no protocol found — define `protocol` (a Protocol) or "
            "STATES/TRANSITIONS/MESSAGES/REQUESTS/RESPONSES"
        )
    if proto.name == "protocol":
        proto.name = getattr(module, "NAME", path.stem)
    return proto, module


def _transition(value: object, index: int) -> tuple[str, str] | tuple[str, str, str]:
    """A transition as `(source, target, message)`, or a located refusal."""
    if not isinstance(value, (list, tuple)) or len(value) not in (2, 3):
        raise InvalidArtifact(
            f"TRANSITIONS[{index}]: expected 2 or 3 names (source, target[, message]), "
            f"not {value!r}"
        )
    parts = tuple(_name(part) for part in value)
    if len(parts) == 2:
        return (parts[0], parts[1])
    return (parts[0], parts[1], parts[2])


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
        transitions=[
            (t[0], t[1], t[2]) if len(t) == 3 else (t[0], t[1]) for t in (transitions or [])
        ],
        start=start,
        terminal=list(terminal or []),
        messages=list(messages or []),
        requests=list(requests or []),
        responses=dict(responses or {}),
        name=name,
    )
