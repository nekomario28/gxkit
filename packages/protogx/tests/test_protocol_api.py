"""The protogx public helpers and a branch no example exercises."""

from __future__ import annotations

from gxcore import ERROR
from gxcore.diagram import image_size as node_image_size
from gxcore.testing import assert_fires
from protogx import Protocol, inspect_protocol, protocol_from_parts
from protogx.render import image_size


def test_protocol_from_parts_roundtrips():
    proto = protocol_from_parts(
        states=["a", "b"],
        transitions=[("a", "b", "SYN")],
        start="a",
        terminal=["b"],
        messages=["SYN"],
    )
    assert proto.states == ["a", "b"]
    assert proto.transitions == [("a", "b", "SYN")]
    assert proto.messages == ["SYN"]


def test_image_size_tracks_the_state_count():
    assert image_size(Protocol(states=["a", "b"])) == node_image_size(2)


def test_a_response_naming_an_undeclared_message():
    proto = Protocol(
        states=["a", "b"],
        start="a",
        terminal=["b"],
        messages=["SYN"],
        transitions=[("a", "b", "SYN")],
        responses={"SYN": "NOPE"},
    )
    assert_fires(inspect_protocol(proto), "unknown-message", ERROR)


def test_load_protocol_from_module_level_transitions(tmp_path):
    from protogx import load_protocol

    src = tmp_path / "p.py"
    src.write_text(
        'STATES = ["a", "b"]\n'
        'TRANSITIONS = [("a", "b", "SYN")]\n'
        'START = "a"\n'
        'TERMINAL = ["b"]\n'
        'MESSAGES = ["SYN"]\n'
        'NAME = "p"\n'
    )
    proto, _module = load_protocol(src)
    assert proto.states == ["a", "b"]
    assert proto.transitions == [("a", "b", "SYN")]
    assert proto.name == "p"
