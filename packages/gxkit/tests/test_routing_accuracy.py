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


def test_the_umbrella_refuses_a_file_that_declares_two_artifacts(tmp_path, capsys):
    """In-process: routing collects every match, and the ambiguity is the refusal.

    A file with both a `Level` and a matplotlib figure was routed to chartgx by
    registry order and reported "no problems", while `levelgx <file>` found
    `no-goal` — the umbrella exit 0.
    """
    pytest.importorskip("matplotlib")
    from gxkit.cli import main

    artifact = tmp_path / "both.py"
    artifact.write_text(
        "import matplotlib\nmatplotlib.use('Agg')\n"
        "import matplotlib.pyplot as plt\n"
        "from levelgx import Level\n"
        "level = Level(rows=['....', '.S..'])\n"
        "fig, ax = plt.subplots()\nax.plot([1, 2], [3, 4])\n",
        encoding="utf-8",
    )
    assert main(["inspect", str(artifact), "--no-storyboard"]) == 2
    err = capsys.readouterr().err
    assert "declares more than one artifact" in err
    assert "chartgx" in err and "levelgx" in err


def test_the_umbrella_reports_an_interrupt_as_the_shells_code(tmp_path, capsys):
    from gxkit.cli import main

    artifact = tmp_path / "interrupt.py"
    artifact.write_text("raise KeyboardInterrupt\n", encoding="utf-8")
    assert main(["inspect", str(artifact), "--no-storyboard"]) == 130
    assert "gxkit: interrupted" in capsys.readouterr().err
