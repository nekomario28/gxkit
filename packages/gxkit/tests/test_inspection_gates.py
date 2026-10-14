"""Public gate regressions: inspection must run before it can succeed."""

from __future__ import annotations

import subprocess
import sys

import pytest


def _inspect(path, *flags):
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
    )


@pytest.mark.parametrize("status", [0, 3, "stop"])
def test_artifact_exit_is_a_load_failure_and_does_not_stop_the_directory(tmp_path, status):
    (tmp_path / "a.py").write_text(f"raise SystemExit({status!r})\n", encoding="utf-8")
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


def test_replacing_an_overlap_partner_is_a_new_error(tmp_path):
    import json

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
