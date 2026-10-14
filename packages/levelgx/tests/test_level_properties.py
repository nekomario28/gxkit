"""Cross-check levelgx's grid reading against NetworkX.

A level is a *guarded* graph: one-way tiles mean "reachable" and "goal still
reachable from here" diverge, and that gap is the soft-lock. The rule is easy to
get subtly wrong (which arrow blocks entry, which blocks exit), so random levels
are also turned into a NetworkX digraph from the documented rule and the two
verdicts must agree.
"""

from __future__ import annotations

import random

import networkx as nx
import pytest
from levelgx import Level, inspect_level
from levelgx.checks import distances, reachable
from levelgx.level import DIRS, ONEWAY

TILES = "#.X!><^v"

SEEDS = range(30)


def _level(rng: random.Random) -> Level:
    h, w = rng.randint(2, 7), rng.randint(2, 7)
    grid = [[rng.choice(TILES) for _ in range(w)] for _ in range(h)]
    cells = [(r, c) for r in range(h) for c in range(w)]
    spawn, goal = rng.sample(cells, 2)
    grid[spawn[0]][spawn[1]] = "S"
    grid[goal[0]][goal[1]] = "G"
    return Level(["".join(row) for row in grid], name="p")


def _spec_graph(level: Level, *, hazards_block: bool = True) -> nx.DiGraph:
    """The rule as written in the docs: enter and leave a one-way only along it."""
    g: nx.DiGraph = nx.DiGraph()
    for r in range(level.height):
        for c in range(level.width):
            if level.passable(r, c, hazards_block=hazards_block):
                g.add_node((r, c))
    for r, c in list(g.nodes()):
        here = level.at(r, c)
        for step in DIRS.values():
            nr, nc = r + step[0], c + step[1]
            if not level.passable(nr, nc, hazards_block=hazards_block):
                continue
            if here in ONEWAY and ONEWAY[here] != step:
                continue  # cannot leave against the arrow
            there = level.at(nr, nc)
            if there in ONEWAY and ONEWAY[there] != step:
                continue  # cannot enter against the arrow
            g.add_edge((r, c), (nr, nc))
    return g


def _codes(report) -> set[str]:
    return {p.code for p in report.problems}


@pytest.mark.parametrize("seed", SEEDS)
def test_reachable_and_distances_match_networkx(seed):
    rng = random.Random(seed)
    for _ in range(30):
        level = _level(rng)
        spawn = level.spawn()
        assert spawn is not None
        g = _spec_graph(level)
        assert reachable(level, spawn) == ({spawn} | set(nx.descendants(g, spawn)))
        assert distances(level, spawn) == dict(nx.shortest_path_length(g, spawn))


@pytest.mark.parametrize("seed", SEEDS)
def test_soft_lock_and_verdicts_match_networkx(seed):
    rng = random.Random(seed)
    for _ in range(30):
        level = _level(rng)
        spawn, goal = level.spawn(), level.goal()
        assert spawn is not None and goal is not None
        g = _spec_graph(level)
        seen = {spawn} | set(nx.descendants(g, spawn))
        can_finish = {goal} | set(nx.ancestors(g, goal))
        report = inspect_level(level)
        codes = _codes(report)

        assert ("goal-unreachable" in codes) == (goal not in seen)
        assert ("stranded-item" in codes) == any(i not in seen for i in level.items())
        assert ("unreachable-area" in codes) == any(n not in seen for n in g.nodes())
        assert ("no-items" in codes) == (not level.items())

        softlocks = [p for p in report.problems if p.code == "soft-lock"]
        if goal in seen:
            traps = seen - can_finish
            assert bool(softlocks) == bool(traps)
            if traps:
                example = min(traps)
                assert softlocks[0].target == f"cell r{example[0]}c{example[1]}"
        else:
            assert not softlocks


@pytest.mark.parametrize("seed", SEEDS)
def test_random_levels_never_raise(seed):
    rng = random.Random(seed)
    for _ in range(30):
        assert isinstance(inspect_level(_level(rng)).problems, list)


def test_hazards_block_the_only_route():
    # corridor: S . ! . G — the hazard is the only way through
    level = Level(["#####", "#S!.G#", "#####"], name="hazard")
    assert "goal-unreachable" in _codes(inspect_level(level))
    assert "hazard-cuts-off" in _codes(inspect_level(level))
