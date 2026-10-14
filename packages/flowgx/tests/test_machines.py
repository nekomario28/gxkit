"""Prove every flowgx check fires on a machine that has the fault.

The core case — a state that can never reach "done" — is the workflow version of
a soft-lock, computed with the same `gxcore.graph` reachability.
"""

from __future__ import annotations

from pathlib import Path

from flowgx import Machine, inspect_machine, load_machine
from gxcore import ERROR, INFO
from gxcore.testing import assert_fires, assert_quiet, has

GOOD = Machine(
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
    name="good",
)

BROKEN = Machine(
    states=["draft", "review", "changes", "published", "limbo", "rejected"],
    start="draft",
    accept=["published"],
    transitions=[
        ("draft", "review", "submit"),
        ("review", "published", "approve"),
        ("review", "changes", "act"),
        ("review", "changes", "act"),
        ("changes", "limbo", "park"),
    ],
    name="broken",
)


def test_good_machine_has_no_errors():
    r = inspect_machine(GOOD)
    assert r.errors == 0
    # the review <-> changes loop is a note, not a problem
    assert has(r, "cycle", INFO)


def test_broken_machine_fires_every_fault():
    r = inspect_machine(BROKEN)
    assert_fires(r, "unreachable-state", ERROR)   # rejected
    assert_fires(r, "dead-end", ERROR)            # limbo
    assert_fires(r, "no-exit", ERROR)             # changes
    assert_fires(r, "ambiguous-transition", ERROR)  # review "act"


def test_no_start():
    m = Machine(states=["a", "b"], accept=["b"], transitions=[("a", "b")], name="x")
    assert_fires(inspect_machine(m), "no-start", ERROR)


def test_no_accept_when_no_terminal():
    m = Machine(states=["a", "b"], start="a", accept=[],
                transitions=[("a", "b"), ("b", "a")], name="x")
    assert_fires(inspect_machine(m), "no-accept", ERROR)


def test_terminal_is_the_default_accept():
    m = Machine(states=["a", "b"], start="a", accept=[], transitions=[("a", "b")], name="x")
    r = inspect_machine(m)
    assert r.errors == 0
    assert "accepting: b" in r.details


def test_unknown_state():
    m = Machine(states=["a", "b"], start="a", accept=["b"],
                transitions=[("a", "c")], name="x")
    assert_fires(inspect_machine(m), "unknown-state", ERROR)


def test_reachable_but_cannot_finish_is_no_exit():
    # a -> b; b -> c; c -> b (cycle with no way to "done"); d is accepting but unreachable
    m = Machine(states=["a", "b", "c", "d"], start="a", accept=["d"],
                transitions=[("a", "b"), ("b", "c"), ("c", "b")], name="x")
    r = inspect_machine(m)
    assert_fires(r, "no-exit", ERROR)
    assert_fires(r, "unreachable-state", ERROR)


def test_good_machine_has_no_phantom_layout_problems():
    r = inspect_machine(GOOD)
    assert_quiet(r, "text-overlap")
    assert_quiet(r, "clipped-text")


def test_examples_load_and_are_diagnosed():
    examples = Path(__file__).resolve().parents[1] / "examples"
    good, _ = load_machine(examples / "good_machine.py")
    broken, _ = load_machine(examples / "broken_machine.py")
    assert inspect_machine(good).errors == 0
    assert inspect_machine(broken).errors >= 3
