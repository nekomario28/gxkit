"""The CLI contract, end to end, for every tool: faulty exits 1, honest exits 0,
and `--json` is valid JSON with at least one error.

This is the promise every README makes; a test for it means a new tool cannot
ship without honouring it.
"""

from __future__ import annotations

import importlib
import json
import pathlib
import shutil

import pytest
from gxcore.cli import run

ROOT = pathlib.Path(__file__).resolve().parents[3]

EXAMPLES = {
    "chartgx": ("good_chart.py", "bad_chart.py"),
    "levelgx": ("good_level.py", "softlock_level.py"),
    "flowgx": ("good_machine.py", "broken_machine.py"),
    "protogx": ("good_protocol.py", "broken_protocol.py"),
    "authzgx": ("good_auth.py", "escalate_auth.py"),
    "depsgx": ("good_modules.py", "broken_modules.py"),
    "schemagx": ("good_schema.py", "broken_schema.py"),
    "docgx": ("good_page.py", "crowded_page.py"),
    "shadergx": ("good_shader.py", "broken_shader.py"),
    "framegx": ("good_clip.py", "frozen_clip.py"),
    "apigx": ("good_api.py", "broken_api.py"),
    "netgx": ("good_network.py", "broken_network.py"),
}


def _example(name: str, filename: str) -> str:
    return str(ROOT / "packages" / name / "examples" / filename)


def _require_capability(name: str) -> None:
    if name == "shadergx":
        gl = pytest.importorskip("shadergx.gl")
        try:
            gl.context()
        except Exception:
            pytest.skip("no GL context")
    if name == "framegx" and not shutil.which("ffprobe"):
        pytest.skip("no ffprobe")


@pytest.mark.parametrize("name", list(EXAMPLES))
def test_contract_faulty_exits_1_honest_exits_0(name, capsys):
    _require_capability(name)
    good, bad = EXAMPLES[name]
    tool = importlib.import_module(f"{name}.tool").TOOL

    assert run(tool, ["inspect", _example(name, good), "--no-storyboard"]) == 0
    assert run(tool, ["inspect", _example(name, bad), "--no-storyboard"]) == 1
    capsys.readouterr()

    assert run(tool, ["inspect", _example(name, bad), "--json", "--no-storyboard"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["errors"] >= 1
    assert report["problems"], f"{name}: --json reported no problems"


def test_the_examples_cover_every_tool():
    from gxkit.registry import TOOLS

    assert set(EXAMPLES) == {tool.name for tool in TOOLS}
