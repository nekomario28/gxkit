"""The composite action's shell, tested without running the action.

The logic lives in `scripts/inspect_path.sh` so it can be linted (shellcheck) and
run directly. These pin the fail-closed behaviour a review found missing: an
empty directory or a missing path is a failure, not a silent success.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "inspect_path.sh"


def _run(target, tmp_path, *, tool="", flags="", exit_code=0):
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    fake = bindir / (tool or "gxkit")
    fake.write_text(f"#!/usr/bin/env bash\nexit {exit_code}\n")
    fake.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}",
        "TARGET": str(target),
        "TOOL": tool,
        "FLAGS": flags,
    }
    return subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True)


def test_an_empty_directory_fails(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    result = _run(empty, tmp_path)
    assert result.returncode == 1
    assert "no *.py artifacts" in result.stdout


def test_a_missing_path_fails(tmp_path):
    result = _run(tmp_path / "nope", tmp_path)
    assert result.returncode == 1
    assert "path not found" in result.stdout


def test_a_file_is_inspected(tmp_path):
    artifact = tmp_path / "a.py"
    artifact.write_text("x = 1\n")
    assert _run(artifact, tmp_path).returncode == 0


def test_a_failing_artifact_propagates(tmp_path):
    artifact = tmp_path / "a.py"
    artifact.write_text("x = 1\n")
    assert _run(artifact, tmp_path, exit_code=1).returncode == 1


def test_a_directory_with_an_artifact_is_inspected(tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "a.py").write_text("x = 1\n")
    assert _run(artifacts, tmp_path).returncode == 0


def test_an_explicit_tool_is_used(tmp_path):
    artifact = tmp_path / "a.py"
    artifact.write_text("x = 1\n")
    result = _run(artifact, tmp_path, tool="levelgx")
    assert result.returncode == 0
    assert "levelgx inspect" in result.stdout
