"""The docs, the registry and the package list must move together.

Adding a tool and forgetting the README, llms.txt or the dispatcher is a classic
avoidable mistake; this makes each one a failing test.
"""

from __future__ import annotations

import importlib
import pathlib
import re
import shutil

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[3]
TOOL_PACKAGES = sorted(
    d.name
    for d in (ROOT / "packages").iterdir()
    if (d / "pyproject.toml").exists() and d.name not in {"gxcore", "gxkit"}
)


def test_package_list_is_what_we_expect():
    assert len(TOOL_PACKAGES) == 10


def test_registry_lists_every_tool_package():
    from gxkit.registry import TOOLS

    assert sorted(t.name for t in TOOLS) == TOOL_PACKAGES


def test_readme_lists_every_tool():
    rows = re.findall(
        r"^\| `([a-z0-9]+gx)` \|", (ROOT / "README.md").read_text(encoding="utf-8"), re.M
    )
    assert sorted(rows) == TOOL_PACKAGES


def test_llms_txt_lists_every_tool():
    names = re.findall(
        r"^- \*\*([a-z0-9]+gx)\*\*", (ROOT / "llms.txt").read_text(encoding="utf-8"), re.M
    )
    assert sorted(names) == TOOL_PACKAGES


def _figure_module():
    import importlib.util

    path = ROOT / "scripts" / "make_readme_figure.py"
    spec = importlib.util.spec_from_file_location("make_readme_figure", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_readme_figure_covers_every_tool():
    module = _figure_module()
    assert sorted(name for name, _, _ in module.TOOLS) == TOOL_PACKAGES
    svg = module.build()
    for name in TOOL_PACKAGES:
        assert name in svg, f"{name} is missing from the architecture figure"
    assert f"{len(TOOL_PACKAGES)} inspect tools" in svg


def test_the_committed_architecture_svg_is_current():
    produced = _figure_module().build()
    assert produced == (ROOT / "docs" / "assets" / "architecture.svg").read_text(encoding="utf-8")


def test_no_stale_tool_count_in_the_readme():
    # a hardcoded "nine" was left behind after the tenth tool landed
    assert "nine inspect tools" not in (ROOT / "README.md").read_text(encoding="utf-8").lower()


# --------------------------------------------------------------------------- #
# drift guards: a name, a count and a version must not go stale in the prose
# --------------------------------------------------------------------------- #

EXTERNAL_GX_NAMES = {"manimgx"}  # another project we mention, not a gxkit tool


def _docs_text():
    for pattern in ("*.md", "*.txt", "*.yml", "*.toml"):
        for path in ROOT.rglob(pattern):
            if any(part in {".git", ".venv", "dist", "__pycache__"} for part in path.parts):
                continue
            yield path


def test_no_unknown_tool_name_in_the_docs():
    canonical = {"gxcore", "gxkit", *TOOL_PACKAGES}
    unknown: dict[str, set[str]] = {}
    for path in _docs_text():
        found = set(re.findall(r"\b([a-z][a-z0-9]*gx)\b", path.read_text(encoding="utf-8")))
        bad = found - canonical - EXTERNAL_GX_NAMES
        if bad:
            unknown[str(path.relative_to(ROOT))] = bad
    assert not unknown, f"unknown tool name(s): {unknown}"


def test_releasing_lists_every_package():
    text = (ROOT / "docs" / "RELEASING.md").read_text(encoding="utf-8")
    match = re.search(r"for p in (.+?); do", text)
    assert match is not None
    assert set(match.group(1).split()) == {"gxcore", "gxkit-cli", *TOOL_PACKAGES}


def test_root_skill_routes_to_every_tool():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    for name in TOOL_PACKAGES:
        assert f"`{name}`" in text, f"SKILL.md does not mention {name}"


def test_release_references_agree_and_are_changelogged():
    refs: set[str] = set()
    for path in (ROOT / "README.md", ROOT / "docs" / "agent-native-landscape.md"):
        text = path.read_text(encoding="utf-8")
        refs |= set(re.findall(r"gxkit@v(\d+\.\d+\.\d+)", text))
        refs |= set(re.findall(r"Status \(v(\d+\.\d+\.\d+)\)", text))
    assert len(refs) == 1, f"release references disagree: {sorted(refs)}"
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{refs.pop()}]" in changelog


# --------------------------------------------------------------------------- #
# the documented example output must be what the tool prints today
# ---------------------------------------------------------------------------

DOCUMENTED_EXAMPLES = {
    "chartgx": "bad_chart.py",
    "levelgx": "softlock_level.py",
    "flowgx": "broken_machine.py",
    "protogx": "broken_protocol.py",
    "authzgx": "escalate_auth.py",
    "depsgx": "broken_modules.py",
    "schemagx": "broken_schema.py",
    "docgx": "crowded_page.py",
    "shadergx": "broken_shader.py",
    "framegx": "frozen_clip.py",
}


def _skip_without_capability(name: str) -> None:
    if name == "shadergx":
        gl = pytest.importorskip("shadergx.gl")
        try:
            gl.context()
        except Exception:
            pytest.skip("no GL context")
    if name == "framegx" and not shutil.which("ffprobe"):
        pytest.skip("no ffprobe")


def _inspect_example(name: str):
    tool = importlib.import_module(f"{name}.tool").TOOL
    artifact = tool.load(ROOT / "packages" / name / "examples" / DOCUMENTED_EXAMPLES[name])
    return tool.inspect(artifact)


def _assert_readme_matches(name: str, readme_path) -> None:
    readme = readme_path.read_text(encoding="utf-8")
    summary = re.search(r"inspect: (\d+) problems? \((\d+) errors?\)", readme)
    assert summary is not None, f"{name}: the README shows no `inspect:` summary"
    report = _inspect_example(name)
    ordered = report.sorted()
    assert (len(ordered), report.errors) == (int(summary.group(1)), int(summary.group(2))), (
        f"{name}: README says {summary.group(0)!r}, the tool prints "
        f"{len(ordered)} problems ({report.errors} errors)"
    )
    for index, severity, code in re.findall(
        r"\[(\d+)\]\s+(error|warn|info)\s+.*?\s([a-z][a-z0-9-]+):", readme
    ):
        assert int(index) <= len(ordered), f"{name}: README shows [{index}] out of range"
        problem = ordered[int(index) - 1]
        assert (problem.severity, problem.code) == (severity, code), (
            f"{name}: README [{index}] says {severity}/{code}, the tool says "
            f"{problem.severity}/{problem.code}"
        )


@pytest.mark.parametrize("name", list(DOCUMENTED_EXAMPLES))
def test_readme_example_matches_the_tool(name):
    _skip_without_capability(name)
    _assert_readme_matches(name, ROOT / "packages" / name / "README.md")


def test_root_readme_example_matches_levelgx():
    _assert_readme_matches("levelgx", ROOT / "README.md")


_NUMBER_WORDS = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
    13: "thirteen",
    14: "fourteen",
    15: "fifteen",
}


def test_readme_names_the_right_domain_count():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    stated = set(re.findall(r"\b([a-z]+) domains\b", readme))
    assert stated, "the README never states the number of domains"
    expected = _NUMBER_WORDS[len(TOOL_PACKAGES)]
    assert stated == {expected}, f"README says {sorted(stated)}, but there are {len(TOOL_PACKAGES)}"


# --------------------------------------------------------------------------- #
# what a tool ships, and the action's documented inputs
# --------------------------------------------------------------------------- #

REQUIRED_TOOL_FILES = ("README.md", "AGENTS.md", "llms.txt", "SKILL.md", "LICENSE")


def test_every_tool_ships_its_agent_docs():
    for name in TOOL_PACKAGES:
        for filename in REQUIRED_TOOL_FILES:
            path = ROOT / "packages" / name / filename
            assert path.exists(), (
                f"{name}/{filename} is missing (README claims every tool ships it)"
            )


def test_each_tool_doc_installs_its_own_package():
    for name in TOOL_PACKAGES:
        for filename in ("README.md", "AGENTS.md", "llms.txt"):
            text = (ROOT / "packages" / name / filename).read_text(encoding="utf-8")
            for sub in re.findall(r"subdirectory=packages/([A-Za-z0-9_]+)", text):
                assert sub == name, f"packages/{name}/{filename} installs packages/{sub}"


def test_readme_action_example_uses_declared_inputs():
    action = (ROOT / "action.yml").read_text(encoding="utf-8")
    declared = set(re.findall(r"^  ([a-z_]+):$", action.split("\nruns:", 1)[0], re.M))
    assert declared == {"path", "tool", "args"}, f"unexpected action inputs: {sorted(declared)}"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    example = re.search(r"uses: nekomario28/gxkit@[0-9v.]+(.*?)```", readme, re.S)
    assert example is not None, "the README has no action example"
    used = set(re.findall(r"^\s+([a-z_]+):", example.group(1), re.M)) - {"with"}
    assert used <= declared, (
        f"the README action example uses undeclared input(s): {used - declared}"
    )
    for inp in declared:
        assert inp in readme, f"the README does not document the {inp!r} input"


def test_every_tool_skill_names_itself():
    for name in TOOL_PACKAGES:
        text = (ROOT / "packages" / name / "SKILL.md").read_text(encoding="utf-8")
        match = re.search(r"^name:\s*(\S+)", text, re.M)
        assert match is not None and match.group(1) == name, f"{name}/SKILL.md name is wrong"


def test_tool_docs_only_name_their_own_codes():
    from gxkit.codes import CODEBOOK

    shared = set(CODEBOOK["gxcore"])  # emitted by the shared layout component
    for name in TOOL_PACKAGES:
        allowed = set(CODEBOOK[name]) | shared
        for filename in ("README.md", "SKILL.md", "AGENTS.md", "llms.txt"):
            text = (ROOT / "packages" / name / filename).read_text(encoding="utf-8")
            for token in re.findall(r"`([a-z][a-z0-9]*-[a-z0-9-]+)`", text):
                assert token in allowed, (
                    f"packages/{name}/{filename} names {token!r}, which {name} does not emit"
                )


# import name -> the dependency it stands for, for the licensing table
_RUNTIME_IMPORTS = {
    "Pillow": "PIL",
    "matplotlib": "matplotlib",
    "numpy": "numpy",
    "moderngl": "moderngl",
}


def _importers(module: str) -> set[str]:
    found: set[str] = set()
    for pkg in sorted((ROOT / "packages").glob("*/src/*")):
        text = "\n".join(p.read_text(encoding="utf-8") for p in pkg.rglob("*.py"))
        if re.search(rf"(^|\n)\s*(import {module}\b|from {module}[ .])", text):
            found.add(pkg.name)
    return found


def test_licensing_table_matches_the_actual_imports():
    text = (ROOT / "docs" / "LICENSING.md").read_text(encoding="utf-8")
    section = text.split("## Dependency licenses", 1)[1].split("## ", 1)[0]
    rows = dict(re.findall(r"^\| (\w+) \| .*? \| (.*?) \|$", section, re.M))
    for dependency, module in _RUNTIME_IMPORTS.items():
        assert dependency in rows, f"the licensing table has no {dependency} row"
        listed = {x.strip() for x in rows[dependency].split(",") if x.strip()}
        assert listed == _importers(module), (
            f"{dependency}: the table says {sorted(listed)}, the imports say "
            f"{sorted(_importers(module))}"
        )
