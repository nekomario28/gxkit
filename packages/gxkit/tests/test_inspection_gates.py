"""Public gate regressions: inspection must run before it can succeed."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest


def _inspect(path, *flags, cwd=None):
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "from gxkit.cli import main; raise SystemExit(main())",
            "inspect",
            str(path),
            "--no-storyboard",
            "--no-config",
            *flags,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
        cwd=cwd,
    )


@pytest.mark.parametrize("status", [0, 3, "stop"])
@pytest.mark.parametrize("stage", ["import", "detection"])
def test_artifact_exit_is_a_load_failure_and_does_not_stop_the_directory(tmp_path, status, stage):
    source = f"raise SystemExit({status!r})\n"
    if stage == "detection":
        source = f"def __getattr__(name):\n    raise SystemExit({status!r})\n"
    (tmp_path / "a.py").write_text(source, encoding="utf-8")
    (tmp_path / "b.py").write_text(
        'from seedgx import SeedSpec, Stream\nspec = SeedSpec(streams=[Stream("bad", None)])\n',
        encoding="utf-8",
    )
    result = _inspect(tmp_path)
    assert result.returncode == 2, result.stderr
    assert "SystemExit" in result.stderr and "missing-seed" in result.stdout
    assert "Traceback" not in result.stderr


def test_auto_detection_and_inspection_share_one_execution_per_invocation(tmp_path):
    from gxkit.cli import main

    counter = tmp_path / "counter.txt"
    artifact = tmp_path / "schedule.py"
    artifact.write_text(
        "from pathlib import Path\nfrom crongx import Run, Schedule\n"
        f"p = Path({str(counter)!r})\n"
        'p.write_text(str(int(p.read_text(encoding="utf-8")) + 1) if p.exists() else "1", encoding="utf-8")\n'
        'schedule = Schedule(runs=[Run("ok", 0, 10)])\n',
        encoding="utf-8",
    )
    args = ["inspect", str(artifact), "--no-storyboard", "--no-config"]
    assert main(args) == 0
    assert counter.read_text(encoding="utf-8") == "1"
    assert main(args) == 0
    assert counter.read_text(encoding="utf-8") == "2"


def test_a_relative_input_keeps_its_identity_when_the_artifact_changes_directory(tmp_path):
    (tmp_path / "elsewhere").mkdir()
    (tmp_path / "artifact.py").write_text(
        'import os\nSTREAMS = [("bad", None)]\nos.chdir("elsewhere")\n', encoding="utf-8"
    )
    (tmp_path / "elsewhere" / "artifact.py").write_text(
        'STREAMS = [("good", 1)]\n', encoding="utf-8"
    )
    result = _inspect("artifact.py", cwd=tmp_path)
    assert result.returncode == 1, result.stdout
    assert "missing-seed" in result.stdout
    assert "artifact.py: artifact" in result.stdout
    assert "Traceback" not in result.stderr


def test_a_direct_tool_reads_its_own_config_directory(tmp_path):
    """Configuration belongs to the artifact's directory, not to wherever it ends up."""
    project = tmp_path / "proj"
    (project / "elsewhere").mkdir(parents=True)
    (tmp_path / "elsewhere").mkdir()
    (project / ".gxkit.toml").write_text('ignore = ["missing-seed"]\n', encoding="utf-8")
    (project / "artifact.py").write_text(
        'import os\nSTREAMS = [("bad", None)]\nos.chdir("../elsewhere")\n', encoding="utf-8"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from seedgx import TOOL\n"
            "from gxcore.cli import run\n"
            "raise SystemExit(run(TOOL, ['inspect', 'artifact.py']))",
        ],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "no problems" in result.stdout


def test_a_report_survives_a_console_that_cannot_encode_it(tmp_path):
    """A verdict must not become an input failure because of a code page."""
    import os

    artifact = tmp_path / "net.py"
    artifact.write_text(
        'NODES = {"known": "service"}\nEDGES = [("known", "ghost")]\n', encoding="utf-8"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from netgx import TOOL\n"
            "from gxcore.cli import run\n"
            f"raise SystemExit(run(TOOL, ['inspect', {str(artifact)!r}]))",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
        env={**os.environ, "PYTHONIOENCODING": "ascii"},
    )
    assert result.returncode == 1, result.stderr
    assert "dangling-edge" in result.stdout
    assert "\\u2192" in result.stdout
    assert "Traceback" not in result.stderr


def test_replacing_an_overlap_partner_is_a_new_error(tmp_path):
    before = tmp_path / "before.py"
    after = tmp_path / "after.py"
    prefix = "from crongx import Run, Schedule\nschedule = Schedule(runs="
    before.write_text(
        prefix + '[Run("a",0,10,"r"),Run("b",30,10,"r"),Run("c",5,10,"r")])\n', encoding="utf-8"
    )
    after.write_text(
        prefix + '[Run("a",30,10,"r"),Run("b",0,10,"r"),Run("c",5,10,"r")])\n', encoding="utf-8"
    )
    baseline = tmp_path / "baseline.json"
    assert _inspect(before, "--write-baseline", str(baseline)).returncode == 1
    result = _inspect(after, "--baseline", str(baseline), "--json")
    assert result.returncode == 1, result.stdout
    assert json.loads(result.stdout)["baseline"] == {
        "new": 1,
        "fixed": 1,
        "persisted": 0,
        "new_errors": 1,
    }


def test_a_rotated_cycle_witness_is_not_new_debt(tmp_path):
    """Two cyclic components, and the fingerprint belongs to the component.

    Which member a cycle search starts from is a display detail, so a baseline
    must recognise the same component after the declaration order changes.
    """
    before = tmp_path / "before.py"
    after = tmp_path / "after.py"
    depends = 'DEPENDS = [("a", "b"), ("b", "a"), ("c", "d"), ("d", "c")]\n'
    before.write_text('MODULES = ["a", "b", "c", "d"]\nROOTS = ["a"]\n' + depends, encoding="utf-8")
    # Declaring the modules in another order moves which member the cycle search
    # starts from: the witness rotates, the component does not.
    after.write_text('MODULES = ["b", "a", "d", "c"]\nROOTS = ["a"]\n' + depends, encoding="utf-8")
    baseline = tmp_path / "baseline.json"
    assert _inspect(before, "--write-baseline", str(baseline)).returncode == 1
    result = _inspect(after, "--baseline", str(baseline), "--json")
    # Nothing is new, so the gate passes: the two cycles and the two unreachable
    # components are the same findings, however the witness rotated.
    assert result.returncode == 0, result.stdout
    diff = json.loads(result.stdout)["baseline"]
    assert diff == {"new": 0, "fixed": 0, "persisted": 4, "new_errors": 0}, diff


def test_every_independent_cycle_is_reported_through_the_cli(tmp_path):
    artifact = tmp_path / "graph.py"
    artifact.write_text(
        'MODULES = ["a", "b", "c", "d"]\n'
        'DEPENDS = [("a", "b"), ("b", "a"), ("c", "d"), ("d", "c")]\n'
        'ROOTS = ["a"]\n',
        encoding="utf-8",
    )
    result = _inspect(artifact, "--json")
    assert result.returncode == 1, result.stdout
    cycles = [p for p in json.loads(result.stdout)["problems"] if p["code"] == "cycle"]
    assert len(cycles) == 2, cycles


def test_replacing_an_unknown_edge_endpoint_is_a_new_error(tmp_path):
    before = tmp_path / "before.py"
    after = tmp_path / "after.py"
    before.write_text(
        'NODES = {"known": "service"}\nEDGES = [("known", "missing_a")]\n', encoding="utf-8"
    )
    after.write_text(
        'NODES = {"known": "service"}\nEDGES = [("known", "missing_b")]\n', encoding="utf-8"
    )
    baseline = tmp_path / "baseline.json"
    assert _inspect(before, "--write-baseline", str(baseline)).returncode == 1
    result = _inspect(after, "--baseline", str(baseline), "--json")
    assert result.returncode == 1, result.stdout
    report = json.loads(result.stdout)
    assert report["errors"] == 1
    assert report["baseline"] == {
        "new": 1,
        "fixed": 1,
        "persisted": 1,
        "new_errors": 1,
    }
