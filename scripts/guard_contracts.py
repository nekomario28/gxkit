"""Check the setup handoff and prove the coverage gate can fail.

These are trusted repository scripts, not a sandbox for arbitrary shell input.
External gate commands are replaced by shell functions; no install, test, audit
or build is actually run. Their real argument vectors, not comments or echo
text, are the evidence. Git installation itself is checked separately as a
consumer operation.

The gate is proven in both directions. Observed argv show the invocation that
must enforce coverage; a failing replay of that invocation shows the failure
reaches the shell. A command whose arguments are right and whose exit status is
discarded is a log line, not a gate.
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


PRELUDE = """
uv() { printf '%s\\0' "$@" >> "$GXKIT_GUARD_LOG"; printf '\\n' >> "$GXKIT_GUARD_LOG"; printf '%s\\n' "$GXKIT_GUARD_ADDOPTS" >> "$GXKIT_GUARD_ENV_LOG"; if [ "${GXKIT_GUARD_FAIL_PYTEST:-0}" = 1 ] && [ "$1" = run ] && [ "$2" = pytest ]; then return 1; fi; }
uvx() { :; }
python3() { :; }
"""


def _run(
    script: str, *, from_file: bool, fail_pytest: bool, addopts: str
) -> tuple[int, list[list[str]], list[str], str]:
    """Execute the script with stubbed gate commands.

    Returns the exit status, the executed pytest argument vectors, the pytest
    options each of those commands inherits from its environment, and output.
    """
    bash = shutil.which("bash")
    assert bash, "a POSIX shell is required to observe executable coverage commands"
    with tempfile.TemporaryDirectory(prefix="gxkit-guard-") as directory:
        root = Path(directory)
        log = root / "calls"
        env_log = root / "environments"
        source = root / "scripts/check.sh"
        source.parent.mkdir()
        source.write_text(script, encoding="utf-8")
        env = {
            **os.environ,
            "GXKIT_GUARD_LOG": str(log),
            "GXKIT_GUARD_ENV_LOG": str(env_log),
            "GXKIT_GUARD_SCRIPT": str(source),
            "GXKIT_GUARD_ADDOPTS": addopts,
            "GXKIT_GUARD_FAIL_PYTEST": "1" if fail_pytest else "0",
        }
        command = 'source "$GXKIT_GUARD_SCRIPT"' if from_file else script
        result = subprocess.run(
            [bash, "-e", "-o", "pipefail", "-c", PRELUDE + command, str(source)],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        calls: list[list[str]] = []
        environments: list[str] = []
        if log.exists():
            for line in log.read_bytes().splitlines():
                argv = line.decode("utf-8").split("\0")
                if argv and argv[-1] == "":
                    argv.pop()
                if argv[:2] == ["run", "pytest"]:
                    calls.append(argv[2:])
        if env_log.exists():
            environments = env_log.read_text(encoding="utf-8").splitlines()
        rendered = "\n".join(" ".join(argv) for argv in calls)
        return result.returncode, calls, environments, rendered + result.stderr


def _pytest_calls(
    script: str, *, from_file: bool = False, addopts: str = ""
) -> tuple[list[list[str]], list[str], str]:
    status, calls, environments, output = _run(
        script, from_file=from_file, fail_pytest=False, addopts=addopts
    )
    assert status == 0, f"coverage script cannot execute: {output}"
    return calls, environments, output


class _StrictLoader(yaml.SafeLoader):
    """A YAML loader that refuses duplicate mapping keys."""


def _no_duplicates(loader, node, deep=False):  # pyyaml callback
    seen: set[object] = set()
    for key_node, _value in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found a duplicate key {key!r} — the last one would silently win",
                key_node.start_mark,
            )
        seen.add(key)
    return loader.construct_mapping(node, deep=deep)


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicates)


def _workflow(root: Path) -> dict:
    """The CI workflow, refusing a document with duplicate keys.

    `yaml.safe_load` keeps the last of a duplicated key and says nothing, so a
    second `env:` block on the coverage step would hide an override behind the
    first one. A workflow this guard cannot read completely is not one it can
    certify.
    """
    return yaml.load(
        (root / ".github/workflows/ci.yml").read_text(encoding="utf-8"), Loader=_StrictLoader
    )


def _require_failure_propagates(script: str, *, from_file: bool, label: str, addopts: str) -> None:
    """A failing coverage run must fail the script that claims to gate on it."""
    status, _calls, _environments, _output = _run(
        script, from_file=from_file, fail_pytest=True, addopts=addopts
    )
    assert status != 0, f"{label}: a failing coverage run is swallowed"


def check_artifacts(root: Path) -> None:
    """Every artifact upload must expire.

    Nothing downloads the built distributions from a CI run, so without a
    retention they accumulate silently — 148 of them and ~53 MB had built up
    before anyone looked.
    """
    workflow = _workflow(root)
    uploads = [
        (job_name, step)
        for job_name, job in workflow["jobs"].items()
        for step in job.get("steps", [])
        if str(step.get("uses", "")).startswith("actions/upload-artifact")
    ]
    assert uploads, "the workflow uploads no artifacts; remove this check with the upload"
    for job_name, step in uploads:
        retention = step.get("with", {}).get("retention-days")
        assert isinstance(retention, int) and 1 <= retention <= 30, (
            f"{job_name}: an uploaded artifact declares no sensible retention-days "
            f"({retention!r}); without one it accumulates"
        )


def _check_calls(
    calls: list[list[str]],
    names: set[str],
    label: str,
    *,
    environments: list[str] | None = None,
) -> None:
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
    # Options an executed command inherits are not argv, but they reach pytest
    # just the same: an inherited --no-cov disables the floor above.
    assert not [value for value in environments or [] if value.strip()], (
        f"{label}: the executed environment overrides pytest options ({environments})"
    )


def check_coverage(root: Path) -> None:
    from gxkit.registry import TOOLS

    names = {"gxcore", "gxkit", *(tool.name for tool in TOOLS)}
    local = (root / "scripts/check.sh").read_text(encoding="utf-8")
    local_calls, local_env, _output = _pytest_calls(local, from_file=True)
    _check_calls(local_calls, names, "scripts/check.sh", environments=local_env)
    _require_failure_propagates(local, from_file=True, label="scripts/check.sh", addopts="")
    workflow = _workflow(root)
    job = workflow["jobs"]["test"]
    assert "if" not in job, "the coverage job must not be conditionally disabled"
    steps = [step for step in job["steps"] if step.get("name") == "Tests with a coverage floor"]
    assert len(steps) == 1 and "if" not in steps[0], (
        "the coverage step must execute unconditionally"
    )
    step = steps[0]
    # Replay the environment this step actually runs in, so an option override
    # cannot disable coverage while the logged arguments still look correct.
    addopts = str({**job.get("env", {}), **step.get("env", {})}.get("PYTEST_ADDOPTS", ""))
    ci_calls, ci_env, _output = _pytest_calls(step["run"], addopts=addopts)
    _check_calls(ci_calls, names, "ci test job", environments=ci_env)
    _require_failure_propagates(step["run"], from_file=False, label="ci test job", addopts=addopts)
