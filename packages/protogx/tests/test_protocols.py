"""Prove every protogx check fires on a protocol that has the fault."""

from __future__ import annotations

from pathlib import Path

from gxcore import ERROR, INFO, WARN
from gxcore.testing import assert_fires
from protogx import Protocol, inspect_protocol, load_protocol

GOOD = Protocol(
    states=["closed", "listen", "established", "closing"],
    start="closed",
    terminal=["closed"],
    messages=["SYN", "ACK", "FIN"],
    transitions=[
        ("closed", "listen", None),
        ("listen", "established", "SYN"),
        ("established", "closing", "FIN"),
        ("closing", "closed", "ACK"),
    ],
    requests=["SYN", "FIN"],
    responses={"SYN": "ACK", "FIN": "ACK"},
    name="good",
)


def test_good_protocol_has_no_errors():
    assert inspect_protocol(GOOD).errors == 0


def test_unknown_state():
    p = Protocol(
        states=["a"], start="a", terminal=["a"], transitions=[("a", "ghost", None)], name="x"
    )
    assert_fires(inspect_protocol(p), "unknown-state", ERROR)


def test_unknown_message():
    p = Protocol(
        states=["a", "b"],
        start="a",
        terminal=["b"],
        messages=["SYN"],
        transitions=[("a", "b", "NOPE")],
        name="x",
    )
    assert_fires(inspect_protocol(p), "unknown-message", ERROR)


def test_unhandled_message():
    p = Protocol(
        states=["a", "b"],
        start="a",
        terminal=["b"],
        messages=["SYN", "RST"],
        transitions=[("a", "b", "SYN")],
        name="x",
    )
    assert_fires(inspect_protocol(p), "unhandled-message", ERROR)


def test_missing_response():
    p = Protocol(
        states=["a", "b"],
        start="a",
        terminal=["b"],
        messages=["SYN", "SYN+ACK"],
        transitions=[("a", "b", "SYN")],
        requests=["SYN"],
        responses={"SYN": "SYN+ACK"},
        name="x",
    )
    assert_fires(inspect_protocol(p), "missing-response", WARN)


def test_nondeterministic():
    p = Protocol(
        states=["a", "b", "c"],
        start="a",
        terminal=["b"],
        transitions=[("a", "b", "SYN"), ("a", "c", "SYN")],
        name="x",
    )
    assert_fires(inspect_protocol(p), "nondeterministic", ERROR)


def test_deadlock():
    p = Protocol(
        states=["a", "dead", "done"],
        start="a",
        terminal=["done"],
        transitions=[("a", "dead", "GO")],
        name="x",
    )
    assert_fires(inspect_protocol(p), "deadlock", ERROR)
    assert_fires(inspect_protocol(p), "no-exit", ERROR)


def test_unreachable_state():
    p = Protocol(
        states=["a", "b", "orphan"],
        start="a",
        terminal=["b"],
        transitions=[("a", "b", "GO")],
        name="x",
    )
    assert_fires(inspect_protocol(p), "unreachable-state", ERROR)


def test_no_terminal_state():
    p = Protocol(
        states=["a", "b"], start="a", transitions=[("a", "b", "GO"), ("b", "a", "BACK")], name="x"
    )
    assert_fires(inspect_protocol(p), "no-terminal", ERROR)


def test_good_protocol_reports_a_cycle_as_a_note():
    assert_fires(inspect_protocol(GOOD), "cycle", INFO)


def test_examples_load_and_are_diagnosed():
    examples = Path(__file__).resolve().parents[1] / "examples"
    good, _ = load_protocol(examples / "good_protocol.py")
    broken, _ = load_protocol(examples / "broken_protocol.py")
    assert inspect_protocol(good).errors == 0
    r = inspect_protocol(broken)
    for code in (
        "unhandled-message",
        "deadlock",
        "unreachable-state",
        "nondeterministic",
    ):
        assert_fires(r, code, ERROR)
    # `no-exit` is for a state that *has* a way out and still cannot finish; the
    # example's stuck state has no exit at all, which is `deadlock`. (An audit of the
    # code names found the documents implied otherwise.)
    assert "no-exit" not in {problem.code for problem in r.problems}
    stuck_but_open = inspect_protocol(
        Protocol(
            states=["a", "b", "c"],
            start="a",
            terminal=["b"],
            messages=["go"],
            transitions=[("a", "b", "go"), ("a", "c", "go"), ("c", "c", "go")],
        )
    )
    assert_fires(stuck_but_open, "no-exit", ERROR)
    assert_fires(stuck_but_open, "nondeterministic", ERROR)
    assert_fires(r, "missing-response", WARN)


def test_a_statement_about_a_state_or_message_that_does_not_exist_is_reported():
    """A terminal state or a request that names nothing is not a deadlock: it is a
    declaration that resolves to nothing, and the protocol would be judged against
    an end condition or a message it does not have."""
    base = dict(
        states=["a", "b"],
        transitions=[("a", "b", "m")],
        start="a",
        terminal=["b"],
        messages=["m"],
        requests={},
        responses={},
    )
    assert inspect_protocol(Protocol(**base)).errors == 0

    report = inspect_protocol(Protocol(**(base | {"terminal": ["ghost"]})))
    assert_fires(report, "unknown-state", ERROR)
    assert "terminal state 'ghost'" in next(
        p.message for p in report.problems if p.code == "unknown-state"
    )

    report = inspect_protocol(Protocol(**(base | {"requests": {"ghost": "m"}})))
    assert_fires(report, "unknown-message", ERROR)
    assert "request names undeclared message 'ghost'" in next(
        p.message for p in report.problems if p.code == "unknown-message"
    )


def test_the_same_transition_twice_is_not_nondeterminism():
    """Deterministic means one target per (state, message), not one declaration.

    Adversarial case from an independent semantics audit (`broken_protocol.py`
    listed the same ACK transition twice and was called non-deterministic).
    """
    identical = Protocol(
        states=["a", "b"],
        messages=["m"],
        transitions=[("a", "b", "m"), ("a", "b", "m")],
        start="a",
        terminal=["b"],
    )
    assert "nondeterministic" not in {
        problem.code for problem in inspect_protocol(identical).problems
    }

    different = Protocol(
        states=["a", "b", "c"],
        messages=["m"],
        transitions=[("a", "b", "m"), ("a", "c", "m")],
        start="a",
        terminal=["b"],
    )
    assert_fires(inspect_protocol(different), "nondeterministic", ERROR)
