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
    rows = re.findall(r"^\| `([a-z0-9]+gx)` \|", (ROOT / "README.md").read_text(), re.M)
    assert sorted(rows) == TOOL_PACKAGES


def test_llms_txt_lists_every_tool():
    names = re.findall(r"^- \*\*([a-z0-9]+gx)\*\*", (ROOT / "llms.txt").read_text(), re.M)
    assert sorted(names) == TOOL_PACKAGES
