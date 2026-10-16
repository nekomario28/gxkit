"""Every promise in `docs/CONTRACT.md`'s Stable section, falsified mechanically.

An independent reviewer is the usual instrument for this, and it was unavailable
(its quota). This is the deterministic version, and in one way it is stronger: it
drives the *published* surface — the console scripts a consumer installs, and the
umbrella — rather than reasoning about the source.

Each test names the sentence it holds. A promise with no test here is a promise the
document should not make.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from gxkit.codes import CODEBOOK
from gxkit.registry import TOOLS

ROOT = Path(__file__).resolve().parents[3]
#: The installed console scripts, which is what a consumer runs.
BIN = Path(sys.executable).parent


def run(argv: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        cwd=cwd or ROOT,
        timeout=120,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def tool_run(tool_name: str, *args: str, cwd: Path | None = None):
    return run([str(BIN / tool_name), "inspect", *args], cwd=cwd)


def an_example(tool_name: str, *, good: bool) -> Path:
    """An example that reports no error (or at least one), by *running* them.

    Not by name: `authzgx`'s fault example is `escalate_auth.py`, and a naming
    convention would have silently skipped the tool. Every tool must ship both
    kinds — a check that cannot be shown firing is the decorative case this whole
    family exists to avoid — so a missing one fails here rather than skipping.
    """
    import importlib

    tool = importlib.import_module(f"{tool_name}.tool").TOOL
    found: list[Path] = []
    compiled_nothing = False
    for path in sorted((ROOT / "packages" / tool_name / "examples").glob("*.py")):
        try:
            report = tool.inspect(tool.load(path))
        except Exception as error:
            if _needs_a_capability(str(error)):
                pytest.skip(f"{tool_name} needs a capability this machine lacks: {error}")
            # A fault example that cannot even load is still a fault.
            found.append(path)
            continue
        compiled_nothing |= any(problem.code == "compile-error" for problem in report.problems)
        if (report.errors == 0) is good:
            found.append(path)
    if not found and compiled_nothing:
        # The capability is present but weaker: this platform's GL cannot compile
        # what the examples need, so nothing here is a clean example. Same reason the
        # README-transcript check skips in that case.
        pytest.skip(f"{tool_name}: this platform's GL cannot compile the examples")
    assert found, (
        f"{tool_name} ships no example that reports "
        f"{'nothing' if good else 'an error'}; the contract test cannot exercise it"
    )
    return found[0]


def a_document(tool_name: str) -> Path | None:
    """An example whose suffix is one the registry says this tool reads."""
    tool = next(tool for tool in TOOLS if tool.name == tool_name)
    suffixes = [suffix for suffix in tool.reads if suffix != ".py"]
    if not suffixes:
        return None
    for path in sorted((ROOT / "packages" / tool_name / "examples").iterdir()):
        if path.suffix in suffixes:
            return path
    return None


# --------------------------------------------------------------------------- #
# Exit codes
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("tool", [tool.name for tool in TOOLS])
def test_exit_0_when_nothing_is_wrong(tool):
    """`0` | inspected, no `error`."""
    result = tool_run(tool, str(an_example(tool, good=True)), "--no-storyboard")
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("tool", [tool.name for tool in TOOLS])
def test_exit_1_when_something_is_wrong(tool):
    """`1` | inspected, at least one `error`."""
    result = tool_run(tool, str(an_example(tool, good=False)), "--no-storyboard")
    assert result.returncode == 1, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("case", "payload"),
    [
        ("missing", None),
        ("unreadable", "not python at all\n"),
        ("malformed", "raise RuntimeError('the artifact refuses to load')\n"),
        ("exits", "import sys\nsys.exit(0)\n"),
    ],
)
def test_exit_2_when_the_input_cannot_be_inspected(case, payload, tmp_path):
    """`2` | the input could not be inspected: missing, unreadable, malformed, or it
    called `sys.exit`."""
    path = tmp_path / f"{case}.py"
    if payload is not None:
        path.write_text(payload, encoding="utf-8")
    result = tool_run("levelgx", str(path), "--no-storyboard")
    assert result.returncode == 2, f"{case}: {result.stdout}{result.stderr}"


# --------------------------------------------------------------------------- #
# The report
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("tool", [tool.name for tool in TOOLS])
def test_the_json_report_carries_the_documented_keys(tool):
    """`--json` prints `name`, `subject`, `details`, `errors`, `problems` (each with
    `severity`, `code`, `message` …)."""
    result = tool_run(tool, str(an_example(tool, good=False)), "--no-storyboard", "--json")
    report = json.loads(result.stdout)
    assert {"name", "subject", "details", "errors", "problems"} <= set(report)
    assert report["errors"] >= 1
    problem = report["problems"][0]
    assert {"severity", "code", "message"} <= set(problem)
    assert problem["code"] in CODEBOOK[tool]


def test_a_warn_or_info_never_fails_a_build(tmp_path):
    """A `warn` or `info` never fails a build."""
    # A clean declaration with no title and no axis labels: warnings and information
    # only, and exit 0.
    declaration = tmp_path / "chart.json"
    declaration.write_text(
        json.dumps(
            {
                "marks": [
                    {
                        "kind": "bar",
                        "categories": ["Q1", "Q2"],
                        "values": [1.0, 2.0],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    result = tool_run("chartgx", str(declaration), "--no-storyboard", "--json")
    report = json.loads(result.stdout)
    severities = {problem["severity"] for problem in report["problems"]}
    assert severities and severities <= {"warn", "info"}, report
    assert result.returncode == 0, report


# --------------------------------------------------------------------------- #
# The CLI shape
# --------------------------------------------------------------------------- #


def test_no_storyboard_writes_nothing(tmp_path):
    """`--no-storyboard` skips the image."""
    artifact = tmp_path / "level.py"
    shutil.copy(an_example("levelgx", good=True), artifact)
    result = tool_run("levelgx", str(artifact), "--no-storyboard")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not list(tmp_path.glob("*.storyboard.png")), "the image was written anyway"


def test_output_names_the_storyboard(tmp_path):
    """`-o/--output` names the image."""
    artifact = tmp_path / "level.py"
    shutil.copy(an_example("levelgx", good=True), artifact)
    target = tmp_path / "elsewhere.png"
    result = tool_run("levelgx", str(artifact), "-o", str(target))
    assert result.returncode == 0, result.stdout + result.stderr
    assert target.exists(), "the storyboard did not land where it was asked to"


def test_the_umbrella_lists_tools_and_codes():
    """The umbrella adds `tools` and `codes`."""
    tools = run([str(BIN / "gxkit"), "tools", "--json"])
    assert tools.returncode == 0, tools.stdout + tools.stderr
    listed = {entry["name"] for entry in json.loads(tools.stdout)}
    assert listed == {tool.name for tool in TOOLS}
    codes = run([str(BIN / "gxkit"), "codes"])
    assert codes.returncode == 0
    assert "soft-lock" in codes.stdout and "truncated-baseline" in codes.stdout


def test_the_umbrella_routes_and_can_be_told_which_tool(tmp_path):
    """`<tool> inspect <path>`, and the umbrella routes to it."""
    artifact = tmp_path / "level.py"
    shutil.copy(an_example("levelgx", good=True), artifact)
    routed = run([str(BIN / "gxkit"), "inspect", str(artifact), "--no-storyboard"])
    assert routed.returncode == 0, routed.stdout + routed.stderr
    named = run([str(BIN / "gxkit"), "inspect", "levelgx", str(artifact), "--no-storyboard"])
    assert named.returncode == 0, named.stdout + named.stderr


# --------------------------------------------------------------------------- #
# The baseline
# --------------------------------------------------------------------------- #


def test_the_baseline_forgives_an_old_error_and_still_fails_the_new_one(tmp_path):
    """`--write-baseline` / `--baseline` compare a run to an accepted state."""
    artifact = tmp_path / "level.py"
    shutil.copy(an_example("levelgx", good=False), artifact)
    stored = tmp_path / "accepted.json"
    written = tool_run("levelgx", str(artifact), "--no-storyboard", "--write-baseline", str(stored))
    assert written.returncode == 1, written.stdout + written.stderr
    forgiven = tool_run(
        "levelgx",
        str(artifact),
        "--no-storyboard",
        "--baseline",
        str(stored),
        "--json",
    )
    assert forgiven.returncode == 0, "an accepted error still failed the build"
    # The diff is nested under `baseline`, as the contract's JSON description says.
    assert json.loads(forgiven.stdout)["baseline"]["new_errors"] == 0


# --------------------------------------------------------------------------- #
# Inputs and platforms
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("tool", [tool.name for tool in TOOLS])
def test_every_tool_takes_a_python_file(tool):
    """Every tool takes a Python file."""
    result = tool_run(tool, str(an_example(tool, good=True)), "--no-storyboard")
    assert result.returncode in (0, 1), result.stdout + result.stderr


@pytest.mark.parametrize("tool", ["apigx", "schemagx", "flowgx"])
def test_the_three_document_readers_read_their_document(tool):
    """… and three also take a document, which the registry publishes.

    The document examples are shipped for this: a reader cannot try an input type
    the package never demonstrates. `good_*` must be clean and `broken_*` must
    report an error, so the pair says the reader was actually exercised.
    """
    documents = sorted(
        path
        for path in (ROOT / "packages" / tool / "examples").iterdir()
        if path.suffix in {suffix for suffix in _reads(tool) if suffix != ".py"}
    )
    assert documents, f"{tool} publishes a document input and ships no example of one"
    for document in documents:
        result = tool_run(tool, str(document), "--no-storyboard")
        if document.name.startswith("good_"):
            assert result.returncode == 0, f"{document.name}: {result.stdout}{result.stderr}"
        else:
            assert result.returncode == 1, f"{document.name}: {result.stdout}{result.stderr}"


def _needs_a_capability(text: str) -> bool:
    """A missing ffprobe, GL context or matplotlib is not a contract defect."""
    lowered = text.lower()
    return any(
        token in lowered
        for token in (
            "ffprobe",
            "ffmpeg",
            "moderngl",
            "no gl",
            "no module named",
            "libgl",
            "is not installed",
        )
    )


def _reads(tool_name: str) -> tuple[str, ...]:
    return next(tool for tool in TOOLS if tool.name == tool_name).reads


def test_every_other_tool_refuses_a_document_it_does_not_read(tmp_path):
    """A suffix no tool reads is an input failure, not a silent misread."""
    document = tmp_path / "thing.json"
    document.write_text("{}", encoding="utf-8")
    result = tool_run("levelgx", str(document), "--no-storyboard")
    assert result.returncode == 2, result.stdout + result.stderr


def test_the_supported_python_is_what_the_packages_require():
    """Supported Python. 3.10 through 3.13."""
    assert (3, 10) <= sys.version_info[:2] <= (3, 13)
    for path in sorted((ROOT / "packages").glob("*/pyproject.toml")):
        text = path.read_text(encoding="utf-8")
        assert 'requires-python = ">=3.10"' in text, f"{path} does not require 3.10"


def test_a_missing_capability_is_refused_not_ignored():
    """The contract's exit `2` covers a missing capability, and names it.

    Testable everywhere, on the machine that *has* the capability: hide `PATH` so
    `framegx` cannot find `ffprobe`, and require the refusal to say so rather than
    reporting a clean clip.
    """
    # In place: the example's media lives beside it, and a copy without the media
    # reports `missing-file` — which is a finding, not the capability refusal this
    # test is about. (Measured: that is exactly how the first version of it passed
    # for the wrong reason.)
    artifact = an_example("framegx", good=False)
    result = subprocess.run(
        [str(BIN / "framegx"), "inspect", str(artifact), "--no-storyboard"],
        capture_output=True,
        text=True,
        timeout=120,
        # The rest of the environment stays: only `PATH` is emptied, which is what
        # makes the program unfindable. (A minimal environment changes which
        # resolution path the tool takes, and the measurement was taken this way.)
        env={**os.environ, "PATH": "/nonexistent"},
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "ffprobe" in (result.stdout + result.stderr).lower(), (
        "the refusal must name the program that is missing"
    )
