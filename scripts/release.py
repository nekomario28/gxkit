#!/usr/bin/env python3
"""Print the publish plan for the family, in dependency order.

Every package depends only on `gxcore`, so the order is a tiny topological sort —
but getting it wrong means an installer cannot resolve `gxcore`. This prints
what to publish, in order, and where the token goes; `scripts/check.sh --full`
builds and checks the artifacts.

    python scripts/release.py
"""

from __future__ import annotations

import pathlib
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

from gxcore.graph import topological_sort

ROOT = pathlib.Path(__file__).resolve().parents[1]


def projects():
    """(directory, distribution name, dependencies) for every package."""
    for pyproject in sorted((ROOT / "packages").glob("*/pyproject.toml")):
        project = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]
        yield pyproject.parent.name, project["name"], list(project.get("dependencies", []))


def internal(dependencies):
    """The dependencies we publish ourselves (not Pillow, matplotlib, …)."""
    known = {name for _, name, _ in projects()}
    found = []
    for dependency in dependencies:
        base = re.split(r"[<>=!~;\[ ]", dependency)[0]
        if base in known:
            found.append(base)
    return found


def publish_order() -> list[str]:
    """Distribution names, dependencies first: `gxcore`, the tools, then `gxkit-cli`."""
    edges = {name: internal(deps) for _, name, deps in projects()}
    ordered = topological_sort(edges)
    # `edges` points from a package to its dependencies; a publish order is its
    # reverse, so the dependency comes first.
    return list(reversed(ordered)) if ordered else []


def main() -> int:
    order = publish_order()
    if not order:
        print("release: the package graph has a cycle", file=sys.stderr)
        return 1
    print("Build and check first:  scripts/check.sh --full")
    print("Then publish in this order (one token publishes all):")
    for position, name in enumerate(order, start=1):
        print(f"  {position}. {name}")
    print("  uv publish dist/*.whl dist/*.tar.gz")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
