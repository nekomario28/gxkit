#!/usr/bin/env python3
"""Publish plan and artifact check for the family.

Two jobs:

* print the publish order, in dependency order (`gxcore` first, `gxkit-cli`
  last) — getting it wrong means an installer cannot resolve `gxcore`;
* `--check` validates a built `dist/` against the `pyproject` files: every
  package has a wheel and an sdist, the versions match, and each wheel carries
  its `LICENSE` and `py.typed` marker.

    python scripts/release.py            # the ordered publish plan
    python scripts/release.py --check    # validate ./dist
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
import zipfile

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

from gxcore.graph import topological_sort

ROOT = pathlib.Path(__file__).resolve().parents[1]


def projects():
    """(directory, distribution name, version, dependencies) for every package."""
    for pyproject in sorted((ROOT / "packages").glob("*/pyproject.toml")):
        project = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]
        yield (
            pyproject.parent.name,
            project["name"],
            project["version"],
            list(project.get("dependencies", [])),
        )


def internal(dependencies):
    """The dependencies we publish ourselves (not Pillow, matplotlib, …)."""
    known = {name for _, name, _, _ in projects()}
    found = []
    for dependency in dependencies:
        base = re.split(r"[<>=!~;\[ ]", dependency)[0]
        if base in known:
            found.append(base)
    return found


def publish_order() -> list[str]:
    """Distribution names, dependencies first: `gxcore`, the tools, `gxkit-cli`."""
    edges = {name: internal(deps) for _, name, _, deps in projects()}
    ordered = topological_sort(edges)
    return list(reversed(ordered)) if ordered else []


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "_", name).lower()


def check_dist(dist_dir) -> list[str]:
    """Every problem with the built artifacts in ``dist_dir`` (empty is good)."""
    dist = pathlib.Path(dist_dir)
    expected = {name: version for _, name, version, _ in projects()}
    problems: list[str] = []

    wheels: dict[str, tuple[str, pathlib.Path]] = {}
    for wheel in sorted(dist.glob("*.whl")):
        parts = wheel.name[: -len(".whl")].split("-")
        if len(parts) < 2:
            problems.append(f"cannot parse wheel name {wheel.name}")
            continue
        wheels[_normalize(parts[0])] = (parts[1], wheel)
    sdists = " ".join(p.name for p in dist.glob("*.tar.gz"))

    for name, version in expected.items():
        key = _normalize(name)
        if key not in wheels:
            problems.append(f"{name}: no wheel in {dist}")
            continue
        found_version, wheel = wheels[key]
        if found_version != version:
            problems.append(f"{name}: wheel version {found_version} != pyproject {version}")
        with zipfile.ZipFile(wheel) as archive:
            members = archive.namelist()
        if not any(m.endswith("licenses/LICENSE") for m in members):
            problems.append(f"{name}: {wheel.name} carries no LICENSE")
        if not any(m.endswith("py.typed") for m in members):
            problems.append(f"{name}: {wheel.name} carries no py.typed")
        if key not in sdists:
            problems.append(f"{name}: no sdist in {dist}")

    for key in sorted(set(wheels) - {_normalize(n) for n in expected}):
        problems.append(f"unexpected wheel {wheels[key][1].name}")
    return problems


def _print_plan() -> int:
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="release", description=__doc__)
    parser.add_argument(
        "--check",
        nargs="?",
        const="dist",
        default=None,
        metavar="DIST",
        help="validate the built artifacts in DIST (default: dist)",
    )
    args = parser.parse_args(argv)
    if args.check is None:
        return _print_plan()
    problems = check_dist(args.check)
    for problem in problems:
        print(f"release: {problem}", file=sys.stderr)
    if problems:
        return 1
    print(f"release: {args.check} matches the pyproject files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
