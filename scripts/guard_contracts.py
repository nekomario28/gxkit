"""Check the setup handoff and observe the coverage commands the shell executes.

These are trusted repository scripts, not a sandbox for arbitrary shell input.
External gate commands are replaced by shell functions; no install, test, audit
or build is actually run. Their real argument vectors, not comments or echo
text, are the evidence. Git installation itself is checked separately as a
consumer operation.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]


def check_agent_prompt(root: Path) -> None:
    readme = re.sub(r"^> ?", "", (root / "README.md").read_text(encoding="utf-8"), flags=re.M)
    block = re.search(r"\*\*Set up with a prompt\.\*\*.*?```\n(.*?)\n```", readme, re.S)
    assert block, "the README has no fenced agent setup prompt"
    prompt = block.group(1)
    url = "https://raw.githubusercontent.com/nekomario28/gxkit/main/llms.txt"
    assert f"Follow {url}." in prompt and "Install gxkit, then inspect" in prompt, (
        "the setup prompt must direct an agent to the family installation"
    )
    llms = (root / "llms.txt").read_text(encoding="utf-8")
    section = re.search(r"^## Install\n(.*?)(?=^## |\Z)", llms, re.M | re.S)
    assert section, "llms.txt has no Install section"
    shell = re.search(r"```sh\n(.*?)\n```", section.group(1), re.S)
    assert shell, "the prompt destination has no shell installation block"
    commands = [shlex.split(line, comments=True) for line in shell.group(1).splitlines()]
    source = "git+https://github.com/nekomario28/gxkit#subdirectory=packages/gxkit"
    assert ["uv", "tool", "install", source] in commands, (
        "the prompt destination has no valid family uv tool install command"
    )
    project = tomllib.loads((root / "packages/gxkit/pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    assert project["name"] == "gxkit-cli" and project["scripts"]["gxkit"] == "gxkit.cli:main"


def _pytest_calls(script: str, *, from_file: bool = False) -> list[list[str]]:
    bash = shutil.which("bash")
    assert bash, "a POSIX shell is required to observe executable coverage commands"
    with tempfile.TemporaryDirectory(prefix="gxkit-guard-") as directory:
        root = Path(directory)
        log = root / "calls"
        source = root / "scripts/check.sh"
        source.parent.mkdir()
        source.write_text(script, encoding="utf-8")
        env = {**os.environ, "GXKIT_GUARD_LOG": str(log), "GXKIT_GUARD_SCRIPT": str(source)}
        prelude = """
uv() { printf '%s\\0' "$@" >> "$GXKIT_GUARD_LOG"; printf '\\n' >> "$GXKIT_GUARD_LOG"; }
uvx() { :; }
python3() { :; }
"""
        command = 'source "$GXKIT_GUARD_SCRIPT"' if from_file else script
        result = subprocess.run(
            [bash, "-e", "-o", "pipefail", "-c", prelude + command, str(source)],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert result.returncode == 0, f"coverage script cannot execute: {result.stderr}"
        calls = (
            [
                line.rstrip(b"\0").decode("utf-8").split("\0")
                for line in log.read_bytes().splitlines()
            ]
            if log.exists()
            else []
        )
        return [argv[2:] for argv in calls if argv[:2] == ["run", "pytest"]]


def _check_calls(calls: list[list[str]], names: set[str], label: str) -> None:
    assert calls, f"{label}: no executed pytest coverage invocation"
    for argv in calls:
        floors = []
        for index, arg in enumerate(argv):
            if arg.startswith("--cov-fail-under="):
                floors.append(arg.split("=", 1)[1])
            elif arg == "--cov-fail-under":
                floors.append(argv[index + 1] if index + 1 < len(argv) else "")
        assert floors == ["100"], f"{label}: pytest must enforce one unambiguous 100% floor"
        assert not {"--no-cov", "--cov-reset"}.intersection(argv), (
            f"{label}: coverage must not be disabled or reset"
        )
        found = {arg.removeprefix("--cov=") for arg in argv if arg.startswith("--cov=")}
        assert found == names, (
            f"{label}: executable coverage membership drifted: {sorted(found ^ names)}"
        )


def check_coverage(root: Path) -> None:
    from gxkit.registry import TOOLS

    names = {"gxcore", "gxkit", *(tool.name for tool in TOOLS)}
    _check_calls(
        _pytest_calls((root / "scripts/check.sh").read_text(encoding="utf-8"), from_file=True),
        names,
        "scripts/check.sh",
    )
    workflow = yaml.safe_load((root / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["test"]
    assert "if" not in job, "the coverage job must not be conditionally disabled"
    steps = [step for step in job["steps"] if step.get("name") == "Tests with a coverage floor"]
    assert len(steps) == 1 and "if" not in steps[0], (
        "the coverage step must execute unconditionally"
    )
    _check_calls(_pytest_calls(steps[0]["run"]), names, "ci test job")
