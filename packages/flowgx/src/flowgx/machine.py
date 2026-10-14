"""A state machine / flowchart, declared as data.

    import flowgx as f

    machine = f.Machine(
        states=["draft", "review", "changes", "published", "archived"],
        start="draft",
        accept=["published", "archived"],
        transitions=[
            ("draft", "review", "submit"),
            ("review", "published", "approve"),
            ("review", "changes", "request"),
            ("changes", "review", "resubmit"),
            ("published", "archived", "archive"),
        ],
    )

Transitions are ``(source, target)`` or ``(source, target, event)``. If
``accept`` is empty, states with no outgoing transition are treated as accepting
("done"), which is the usual meaning of a terminal state.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from gxcore.graph import terminals

Transition = tuple[str, str] | tuple[str, str, str]


@dataclass
class Machine:
    states: list[str] = field(default_factory=list)
    transitions: list[Transition] = field(default_factory=list)
    start: str | None = None
    accept: list[str] = field(default_factory=list)
    name: str = "machine"

    # -- structure -------------------------------------------------------- #

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

    def pair_set(self) -> set[tuple[str, str]]:
        return set(self.pairs())

    def edge_label(self, src: str, dst: str) -> str | None:
        for t in self.transitions:
            if t[0] == src and t[1] == dst and len(t) == 3:
                return t[2]
        return None

    def events(self) -> list[tuple[str, str | None]]:
        return [(t[0], t[2] if len(t) == 3 else None) for t in self.transitions]

    def edges(self) -> dict[str, list[str]]:
        e: dict[str, list[str]] = {s: [] for s in self.all_states()}
        for t in self.transitions:
            e.setdefault(t[0], []).append(t[1])
            e.setdefault(t[1], [])
        return e

    def accepting(self) -> set[str]:
        if self.accept:
            return set(self.accept)
        states = self.all_states()
        return set(terminals(self.edges(), states))

    def referenced(self) -> list[str]:
        out: list[str] = []
        for t in self.transitions:
            for s in (t[0], t[1]):
                if s not in out:
                    out.append(s)
        return out


def _as_machine(value: object) -> Machine | None:
    if isinstance(value, Machine):
        return value
    return None


def load_machine(path: str | Path) -> tuple[Machine, object]:
    """Load a machine from ``machine``/``MACHINE``, or build one from
    module-level ``STATES``/``TRANSITIONS``/``START``/``ACCEPT`` lists."""
    from gxcore.loading import load_module, resolve

    path = Path(path)
    module = load_module(path)
    machine = resolve(
        module,
        attrs=("machine", "MACHINE", "flow", "automaton"),
        builders=("build", "make_machine", "make"),
        convert=_as_machine,
    )
    if machine is None:
        transitions = getattr(module, "TRANSITIONS", getattr(module, "transitions", None))
        if transitions is not None:
            machine = Machine(
                states=list(getattr(module, "STATES", getattr(module, "states", []))),
                transitions=[
                    (t[0], t[1], t[2]) if len(t) == 3 else (t[0], t[1]) for t in transitions
                ],
                start=getattr(module, "START", getattr(module, "start", None)),
                accept=list(getattr(module, "ACCEPT", getattr(module, "accept", []))),
            )
    if machine is None:
        raise ValueError(
            f"{path}: no machine found — define `machine` (a flowgx Machine) "
            "or `STATES`/`TRANSITIONS`/`START`/`ACCEPT`"
        )
    if machine.name == "machine":
        machine.name = getattr(module, "NAME", path.stem)
    return machine, module


def machine_from_parts(
    states: Iterable[str] | None = None,
    transitions: Iterable[Transition] | None = None,
    start: str | None = None,
    accept: Iterable[str] | None = None,
    name: str = "machine",
) -> Machine:
    return Machine(
        states=list(states or []),
        transitions=[
            (t[0], t[1], t[2]) if len(t) == 3 else (t[0], t[1]) for t in (transitions or [])
        ],
        start=start,
        accept=list(accept or []),
        name=name,
    )
