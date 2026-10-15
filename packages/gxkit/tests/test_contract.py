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
    "envgx": ("good_env.py", "broken_env.py"),
    "pipegx": ("good_pipeline.py", "broken_pipeline.py"),
    "seedgx": ("good_seed.py", "broken_seed.py"),
    "crongx": ("good_schedule.py", "broken_schedule.py"),
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


@pytest.mark.parametrize("name", list(EXAMPLES))
def test_a_baseline_round_trips_for_every_tool(tmp_path, capsys, name):
    """Accepting an artifact and re-inspecting it reports nothing new.

    The baseline is the "keep history" half of the contract, and every tool
    supplies its own identities — which is where three real defects were found. A
    round trip over the untouched artifact must therefore be all-persisted and
    exit 0 for every one of them.
    """
    _require_capability(name)
    tool = importlib.import_module(f"{name}.tool").TOOL
    baseline = tmp_path / f"{name}.baseline.json"
    faulty = _example(name, EXAMPLES[name][1])

    assert run(tool, ["inspect", faulty, "--write-baseline", str(baseline), "--no-storyboard"]) == 1
    captured = capsys.readouterr()
    assert baseline.exists(), f"{name}: no baseline written ({captured.err})"

    assert (
        run(tool, ["inspect", faulty, "--baseline", str(baseline), "--json", "--no-storyboard"])
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["baseline"] == {
        "new": 0,
        "fixed": 0,
        "persisted": len(report["problems"]),
        "new_errors": 0,
    }, f"{name}: {report['baseline']} for {len(report['problems'])} problems"


def test_the_examples_cover_every_tool():
    from gxkit.registry import TOOLS

    assert set(EXAMPLES) == {tool.name for tool in TOOLS}
