"""The docs, the registry and the package list must move together.

Adding a tool and forgetting the README, llms.txt or the dispatcher is a classic
avoidable mistake; this makes each one a failing test.
"""

from __future__ import annotations

import pathlib
import re

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
