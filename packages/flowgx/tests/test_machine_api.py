"""The flowgx public helpers."""

from __future__ import annotations

from flowgx import machine_from_parts


def test_machine_from_parts_roundtrips():
    machine = machine_from_parts(
        states=["a", "b"], transitions=[("a", "b", "go")], start="a", accept=["b"]
    )
    assert machine.states == ["a", "b"]
    assert machine.transitions == [("a", "b", "go")]
    assert machine.accept == ["b"]


def test_as_machine_rejects_a_non_machine():
    from flowgx.machine import _as_machine

    assert _as_machine("x") is None


def test_load_machine_from_module_level_transitions(tmp_path):
    from flowgx import load_machine

    src = tmp_path / "m.py"
    src.write_text(
        'STATES = ["a", "b"]\nTRANSITIONS = [("a", "b")]\nSTART = "a"\nACCEPT = ["b"]\nNAME = "m"\n'
    )
    machine, _module = load_machine(src)
    assert machine.states == ["a", "b"]
    assert machine.accept == ["b"]


def test_edge_label_returns_the_message_of_a_labelled_transition():
    machine = machine_from_parts(states=["a", "b"], transitions=[("a", "b", "go"), ("b", "a")])
    assert machine.edge_label("a", "b") == "go"
    assert machine.edge_label("b", "a") is None


def test_events_pairs_each_transition_with_its_message():
    machine = machine_from_parts(states=["a", "b"], transitions=[("a", "b", "go"), ("b", "a")])
    assert machine.events() == [("a", "go"), ("b", None)]


def test_pair_set_is_the_deduplicated_pairs():
    machine = machine_from_parts(states=["a", "b"], transitions=[("a", "b", "x"), ("a", "b", "y")])
    assert machine.pair_set() == {("a", "b")}
