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


def test_a_replaced_duplicate_edge_is_not_the_same_finding(tmp_path):
    """Two duplicate findings can share a target; the relationship identifies them.

    `duplicate-edge` reports against its source, so replacing which destination is
    duplicated is a different finding at the same location. Without an identity it
    reads as unchanged debt.
    """
    before = tmp_path / "before.py"
    after = tmp_path / "after.py"
    preamble = 'NODES = {"a": "service", "b": "service", "c": "service"}\n'
    before.write_text(preamble + 'EDGES = [("a", "b"), ("a", "b")]\n', encoding="utf-8")
    after.write_text(preamble + 'EDGES = [("a", "c"), ("a", "c")]\n', encoding="utf-8")
    baseline = tmp_path / "baseline.json"
    assert _inspect(before, "--write-baseline", str(baseline)).returncode == 0
    result = _inspect(after, "--baseline", str(baseline), "--json")
    # The replaced duplicate edge and the moved isolated node are both new/fixed;
    # only `no-public` is the same finding in both. Without a relationship
    # identity the replaced edge would read as persisted, which is the bug.
    assert json.loads(result.stdout)["baseline"] == {
        "new": 2,
        "fixed": 2,
        "persisted": 1,
        "new_errors": 0,
    }


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


def test_a_file_declaring_two_artifacts_is_not_routed_to_one_of_them(tmp_path):
    """Routing by registry order hid the other artifact's error.

    Measured: a file with both a `Level` and a matplotlib figure was routed to
    chartgx and reported "no problems", while `levelgx <file>` found `no-goal`. The
    ambiguity is now refused with the tool to name.
    """
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    artifact = tmp_path / "both.py"
    artifact.write_text(
        "import matplotlib\nmatplotlib.use('Agg')\n"
        "import matplotlib.pyplot as plt\n"
        "from levelgx import Level\n"
        "level = Level(rows=['....', '.S.G'])\n"
        "fig, ax = plt.subplots()\nax.plot([1, 2], [3, 4])\n",
        encoding="utf-8",
    )
    result = _inspect(artifact)
    assert result.returncode == 2, result.stdout
    assert "declares more than one artifact" in result.stderr
    assert "levelgx" in result.stderr and "chartgx" in result.stderr


def test_an_artifact_that_ends_the_process_is_a_refusal_not_a_verdict(tmp_path):
    """`os._exit` is not an exception, so the exit code became the verdict.

    Measured: `os._exit(0)` printed nothing and exited 0 — "inspected, no error" —
    and `os._exit(42)` exited 42, outside the contract's table.
    """
    for status in (0, 1, 42):
        artifact = tmp_path / f"exit{status}.py"
        artifact.write_text(f"import os\nos._exit({status})\n", encoding="utf-8")
        result = _inspect(artifact)
        assert result.returncode == 2, (status, result.stdout, result.stderr)
        assert f"os._exit({status})" in result.stderr
        assert "no problems" not in result.stdout


def test_an_interrupt_is_the_shells_code_without_a_traceback(tmp_path):
    """An artifact can raise `KeyboardInterrupt`; Ctrl-C is the same event.

    Measured: it escaped as a traceback from the entry point and exit 130, which is
    not in the exit table, while the contract promises a refusal for a broken
    artifact.
    """
    artifact = tmp_path / "interrupt.py"
    artifact.write_text("raise KeyboardInterrupt\n", encoding="utf-8")
    result = _inspect(artifact)
    assert result.returncode == 130, (result.stdout, result.stderr)
    assert "interrupted" in result.stderr
    assert "Traceback" not in result.stderr
    # The umbrella and a single tool are two entry points into the same handler, and
    # both must answer the same way.
    direct = subprocess.run(
        [
            sys.executable,
            "-c",
            "from levelgx import TOOL\n"
            "from gxcore.cli import run\n"
            f"raise SystemExit(run(TOOL, ['inspect', {str(artifact)!r}, '--no-storyboard']))",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert direct.returncode == 130, (direct.stdout, direct.stderr)
    assert "interrupted" in direct.stderr
    assert "Traceback" not in direct.stderr


def test_a_baseline_for_another_tool_is_refused_rather_than_compared(tmp_path):
    """A baseline whose records can never match reports every finding as new.

    Measured: a chartgx baseline compared against a levelgx artifact reported
    "1 new, 2 fixed" — the level's error became debt that had apparently been paid.
    """
    other = tmp_path / "chart.json"
    other.write_text(
        '{"marks": [{"kind": "bar", "categories": ["a"], "values": [1.0]}], "title": "t"}',
        encoding="utf-8",
    )
    baseline = tmp_path / "chart_base.json"
    written = subprocess.run(
        [
            sys.executable,
            "-c",
            "from gxkit.cli import main; raise SystemExit(main())",
            "inspect",
            "chartgx",
            str(other),
            "--no-storyboard",
            "--write-baseline",
            str(baseline),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert written.returncode in (0, 1), written.stderr
    level = tmp_path / "level.py"
    level.write_text(
        "from levelgx import Level\nlevel = Level(rows=['....', '.S..'])\n", encoding="utf-8"
    )
    result = _inspect(level, "--baseline", str(baseline))
    assert result.returncode == 2, result.stdout
    assert "baseline for another one" in result.stderr
    # Writing a baseline from one revision and comparing another *is* the workflow:
    # the same artifact's own baseline must still compare (and its own finding, still
    # present, must not read as new).
    own = tmp_path / "level_base.json"
    assert _inspect(level, "--write-baseline", str(own)).returncode == 1
    compared = _inspect(level, "--baseline", str(own), "--json")
    assert compared.returncode == 0, compared.stdout
    assert json.loads(compared.stdout)["baseline"]["new_errors"] == 0
