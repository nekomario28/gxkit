"""Cross-check protogx's reachability reading against NetworkX.

`protogx` answers "which states are unreachable", "where does the machine get
stuck", "which states can never reach a terminal". Those are graph questions
and the risk is an interpretation drift (does the start count as reachable? is a
terminal its own "can finish"?). Every random protocol is also read by NetworkX
and the verdicts must agree.
"""

from __future__ import annotations

import random

import networkx as nx
import pytest
from protogx import Protocol, inspect_protocol

SEEDS = range(30)


def _protocol(rng: random.Random) -> Protocol:
    n = rng.randint(1, 9)
    states = [f"s{i}" for i in range(n)]
    start = rng.choice(states)
    terminal = rng.sample(states, rng.randint(1, n))
    transitions = [(rng.choice(states), rng.choice(states)) for _ in range(rng.randint(0, n * 2))]
    return Protocol(
        states=states,
        transitions=transitions,
        start=start,
        terminal=terminal,
        name="p",
    )


def _nx(proto: Protocol) -> nx.DiGraph:
    g: nx.DiGraph = nx.DiGraph()
    g.add_nodes_from(proto.all_states())
    for t in proto.transitions:
        g.add_edge(t[0], t[1])
    return g


def _targets(report, code: str) -> set[str]:
    return {p.target for p in report.problems if p.code == code and p.target}


def _reference(proto: Protocol) -> tuple[set[str], set[str], set[str], set[str]]:
    state_list = proto.all_states()
    states = set(state_list)
    g = _nx(proto)
    start = proto.start if proto.start in states else (state_list[0] if state_list else None)
    reach = ({start} | set(nx.descendants(g, start))) if start else set()
    accepting = (
        set(proto.terminal) if proto.terminal else {n for n in state_list if g.out_degree(n) == 0}
    )

    gr = g.reverse(copy=True)
    can_finish = set(accepting)
    for t in accepting:
        can_finish |= set(nx.descendants(gr, t))

    dead: set[str] = set()
    no_exit: set[str] = set()
    for s in reach - accepting:
        if g.out_degree(s) == 0:
            dead.add(s)
        elif s not in can_finish:
            no_exit.add(s)
    return set(states) - reach, dead, no_exit, accepting


@pytest.mark.parametrize("seed", SEEDS)
def test_graph_verdicts_match_networkx(seed):
    rng = random.Random(seed)
    for _ in range(30):
        proto = _protocol(rng)
        report = inspect_protocol(proto)
        unreachable, dead, no_exit, accepting = _reference(proto)

        assert _targets(report, "unreachable-state") == unreachable
        assert _targets(report, "deadlock") == dead
        assert _targets(report, "no-exit") == no_exit
        assert proto.accepting() == accepting


@pytest.mark.parametrize("seed", SEEDS)
def test_random_protocols_never_raise(seed):
    rng = random.Random(seed)
    for _ in range(30):
        assert isinstance(inspect_protocol(_protocol(rng)).problems, list)


def test_accepting_falls_back_to_graph_terminals():
    proto = Protocol(states=["a", "b", "c"], transitions=[("a", "b"), ("b", "c")], start="a")
    g = _nx(proto)
    assert proto.accepting() == {n for n in proto.all_states() if g.out_degree(n) == 0}
