"""Prove every levelgx check fires on a level that has the defect.

Includes the check a screenshot cannot make: a soft-lock, where the goal is
solvable but a reachable one-way tile traps the player forever.
"""

from __future__ import annotations

import pytest

from gxcore import ERROR, INFO, WARN
from gxcore.testing import assert_fires, assert_quiet, count, has
from levelgx import Level, can_reach, inspect_level, load_level, reachable

GOOD = [
    "#########",
    "#S......#",
    "#.#####.#",
    "#X....#G#",
    "#########",
]

HAZARD = [
    "#########",
    "#S..!...#",
    "#.#####.#",
    "#X....#G#",
    "#########",
]

SOFTLOCK = [
    "#######",
    "#S...G#",
    "#.#v#.#",
    "#X#.#.#",
    "#######",
]

STRANDED = [
    "#####",
    "#S.G#",
    "#####",
    "#X###",
    "#####",
]


def level(rows):
    return Level(list(rows))


# --------------------------------------------------------------------------- #
# the clean control
# --------------------------------------------------------------------------- #

def test_good_level_is_clean():
    r = inspect_level(level(GOOD))
    assert r.errors == 0
    assert r.problems == []
    assert any("shortest path" in d for d in r.details)


def test_shortest_path_is_reported():
    r = inspect_level(level(GOOD))
    # S(1,1) -> across to (1,7) -> down to G: 8 steps
    assert any("shortest path to goal" in d for d in r.details)


# --------------------------------------------------------------------------- #
# structural errors
# --------------------------------------------------------------------------- #

def test_no_spawn():
    r = inspect_level(level(["###", "#.G#", "###"]))
    assert_fires(r, "no-spawn", ERROR)


def test_no_goal():
    r = inspect_level(level(["###", "#S.#", "###"]))
    assert_fires(r, "no-goal", ERROR)


def test_hazard_cuts_the_only_route():
    r = inspect_level(level(HAZARD))
    assert_fires(r, "goal-unreachable", ERROR)
    assert_fires(r, "hazard-cuts-off", WARN)
    assert_fires(r, "unreachable-area", INFO)


def test_stranded_item():
    r = inspect_level(level(STRANDED))
    assert_fires(r, "stranded-item", ERROR)
    # the walled box holding the item is dead space too
    assert_fires(r, "unreachable-area", INFO)


# --------------------------------------------------------------------------- #
# soft-lock — the directed-graph check
# --------------------------------------------------------------------------- #

def test_softlock_is_an_error():
    r = inspect_level(level(SOFTLOCK))
    assert_fires(r, "soft-lock", ERROR)


def test_softlock_cells_are_reachable_but_cannot_reach_goal():
    lv = level(SOFTLOCK)
    spawn, goal = lv.spawn(), lv.goal()
    seen = reachable(lv, spawn)
    safe = can_reach(lv, {goal})
    traps = seen - safe - {goal}
    assert (2, 3) in seen and (2, 3) not in safe
    assert (3, 3) in seen and (3, 3) not in safe
    assert traps == {(2, 3), (3, 3)}


def test_level_without_one_way_has_no_soft_lock():
    r = inspect_level(level(GOOD))
    assert_quiet(r, "soft-lock")


# --------------------------------------------------------------------------- #
# one-way semantics
# --------------------------------------------------------------------------- #

def test_one_way_only_allows_its_direction():
    lv = level([
        "#####",
        "#S>.#",
        "#####",
    ])
    # entering the '>' from the west is allowed...
    assert (1, 2) in lv.neighbors(1, 1)
    # ...leaving it must go east, so it cannot go back west...
    assert (1, 1) not in lv.neighbors(1, 2)
    # ...and the cell east of it cannot step back west into the '>'.
    assert (1, 2) not in lv.neighbors(1, 3)


def test_documented_examples_load_and_are_diagnosed():
    from pathlib import Path

    examples = Path(__file__).resolve().parents[1] / "examples"
    good, _ = load_level(examples / "good_level.py")
    soft, _ = load_level(examples / "softlock_level.py")
    broken, _ = load_level(examples / "broken_level.py")
    assert inspect_level(good).errors == 0
    assert_fires(inspect_level(soft), "soft-lock", ERROR)
    assert_fires(inspect_level(broken), "goal-unreachable", ERROR)


def test_report_details_describe_the_level():
    r = inspect_level(level(GOOD))
    assert r.details[0].startswith("9x5")
    assert any("reachable from spawn" in d for d in r.details)
