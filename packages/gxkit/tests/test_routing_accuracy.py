"""Routing accuracy on the *real* example files, not fake classes.

`test_registry` proves `detect` reads a class name. This proves it reads the
artifacts the tools actually ship: every example must route to its own tool. A
marker that quietly wins over a class, or an example that stops being
detectable, is a wrong tool run on the user's file.
"""

from __future__ import annotations

import pathlib

import pytest
from gxcore.loading import load_module
from gxkit import detect

ROOT = pathlib.Path(__file__).resolve().parents[3]
EXAMPLES = sorted((ROOT / "packages").glob("*/examples/*.py"))


def _id(path: pathlib.Path) -> str:
    return f"{path.parent.parent.name}/{path.name}"


def test_there_are_examples_to_check():
    assert EXAMPLES, "no examples found — the glob is wrong"


@pytest.mark.parametrize("path", EXAMPLES, ids=_id)
def test_every_example_routes_to_its_own_tool(path):
    tool = path.parent.parent.name
    try:
        module = load_module(path)
    except ModuleNotFoundError as exc:  # an optional dependency (matplotlib, moderngl)
        pytest.skip(f"{tool}: {exc}")
    spec = detect(module)
    assert spec is not None, f"{tool}/{path.name}: not detected"
    assert spec.name == tool, f"{tool}/{path.name}: routed to {spec.name}"


def test_class_match_beats_a_marker():
    from types import SimpleNamespace

    class Machine: ...

    # a file with both a real Machine and protocol-ish markers must be flowgx
    ns = SimpleNamespace(machine=Machine(), MESSAGES=["SYN"], PROTOCOL=object())
    assert detect(ns).name == "flowgx"
