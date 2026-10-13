"""levelgx's domain knowledge: is this level actually playable?

Reachability alone is not enough, because one-way tiles make the level a
*guarded* graph: a cell can be reachable while the goal is not reachable *from*
it. That gap is a soft-lock — the player gets in and cannot get out — and it is
the check that a screenshot review will never catch.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from gxcore import ERROR, INFO, WARN, Problem, Report
from gxcore.geometry import union

from .level import HAZARD, ONEWAY, WALL, Level
from .render import cell_box


# --------------------------------------------------------------------------- #
# reachability
# --------------------------------------------------------------------------- #

def _all_edges(level: Level, *, hazards_block: bool = True) -> dict[tuple[int, int], list[tuple[int, int]]]:
    edges: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for r in range(level.height):
        for c in range(level.width):
            if level.passable(r, c, hazards_block=hazards_block):
                edges[(r, c)] = level.neighbors(r, c, hazards_block=hazards_block)
    return edges


def reachable(level: Level, start: tuple[int, int], *, hazards_block: bool = True) -> set[tuple[int, int]]:
    edges = _all_edges(level, hazards_block=hazards_block)
    if start not in edges:
        return set()
    seen = {start}
    q = deque([start])
    while q:
        u = q.popleft()
        for v in edges.get(u, ()):
            if v not in seen:
                seen.add(v)
                q.append(v)
    return seen


def can_reach(level: Level, targets: set[tuple[int, int]], *, hazards_block: bool = True) -> set[tuple[int, int]]:
    """Cells from which at least one target is reachable (reverse BFS)."""
    edges = _all_edges(level, hazards_block=hazards_block)
    radj: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for u, vs in edges.items():
        for v in vs:
            radj[v].append(u)
    seen = set(targets)
    q = deque(targets)
    while q:
        v = q.popleft()
        for u in radj[v]:
            if u not in seen:
                seen.add(u)
                q.append(u)
    return seen


def distances(level: Level, start: tuple[int, int], *, hazards_block: bool = True) -> dict[tuple[int, int], int]:
    edges = _all_edges(level, hazards_block=hazards_block)
    if start not in edges:
        return {}
    dist = {start: 0}
    q = deque([start])
    while q:
        u = q.popleft()
        for v in edges.get(u, ()):
            if v not in dist:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist


# --------------------------------------------------------------------------- #
# report helpers
# --------------------------------------------------------------------------- #

def _cell_target(cell: tuple[int, int]) -> str:
    return f"cell r{cell[0]}c{cell[1]}"


def _cell_bbox(cell: tuple[int, int]) -> tuple[float, float, float, float]:
    return cell_box(*cell)


def _bbox_of(cells) -> tuple[float, float, float, float] | None:
    return union([_cell_bbox(c) for c in cells])


# --------------------------------------------------------------------------- #
# checks
# --------------------------------------------------------------------------- #

def inspect_level(level: Level, name: str | None = None) -> Report:
    name = name or level.name
    spawn = level.spawn()
    goal = level.goal()
    items = level.items()
    hazards = level.hazards()
    oneways = level.find(*ONEWAY.keys())
    floor = [(r, c) for r in range(level.height) for c in range(level.width)
             if level.is_floor(r, c) and level.at(r, c) != HAZARD]

    report = Report(
        name=name,
        subject=f"level: {level.width}x{level.height}",
        details=[f"{level.width}x{level.height}, {len(items)} items, "
                 f"{len(hazards)} hazards, {len(oneways)} one-way tiles"],
    )
    out: list[Problem] = []

    if spawn is None:
        out.append(Problem(ERROR, "no-spawn", "the level has no spawn tile 'S'"))
    if goal is None:
        out.append(Problem(ERROR, "no-goal", "the level has no goal tile 'G'"))
    if spawn is None or goal is None:
        report.problems = out
        return report

    seen = reachable(level, spawn)
    report.details.append(
        f"reachable from spawn: {len(seen)}/{len(floor)} floor cells"
    )

    if goal in seen:
        report.details.append(f"shortest path to goal: {distances(level, spawn).get(goal, 0)} steps")
    else:
        out.append(Problem(
            ERROR, "goal-unreachable",
            "the goal cannot be reached from the spawn; the level is not playable",
            target=_cell_target(goal), bbox=_cell_bbox(goal),
        ))
        without_hazards = reachable(level, spawn, hazards_block=False)
        if goal in without_hazards:
            out.append(Problem(
                WARN, "hazard-cuts-off",
                "the goal is reachable only if the hazards are ignored — a hazard "
                "blocks the only route",
                target=_cell_target(goal), bbox=_cell_bbox(goal),
            ))

    # Items the player can never pick up.
    for item in items:
        if item not in seen:
            out.append(Problem(
                ERROR, "stranded-item",
                "an item cannot be reached from the spawn",
                target=_cell_target(item), bbox=_cell_bbox(item),
            ))

    # Soft-lock: reachable cells from which the goal is no longer reachable.
    if goal in seen:
        safe = can_reach(level, {goal})
        traps = seen - safe - {goal}
        if traps:
            example = min(traps)
            out.append(Problem(
                ERROR, "soft-lock",
                f"{len(traps)} reachable cells cannot get back to the goal "
                f"(e.g. {_cell_target(example)}) — a one-way tile makes a dead end",
                target=_cell_target(example), bbox=_bbox_of(traps),
            ))

    # Floor the player never reaches: dead space.
    dead = [c for c in floor if c not in seen]
    if dead:
        out.append(Problem(
            INFO, "unreachable-area",
            f"{len(dead)} of {len(floor)} floor cells can never be reached from the spawn",
            bbox=_bbox_of(dead),
        ))

    if not items:
        out.append(Problem(INFO, "no-items", "the level has no items to collect"))

    report.problems = out
    return report
