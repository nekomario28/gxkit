"""Package metadata must stay consistent across the whole family.

A stray `requires-python`, a missing `LICENSE`, a tool that forgot to pin
`gxcore`, a wrong command name, or a URL key only one package has — each is a
PyPI defect that nothing else catches. This scans every package's `pyproject`.
"""

from __future__ import annotations

import pathlib
import re

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

PACKAGES = pathlib.Path(__file__).resolve().parents[2]
TOOLS = sorted(
    d.name
    for d in PACKAGES.iterdir()
    if (d / "pyproject.toml").exists() and d.name not in {"gxcore", "gxkit"}
)


def _projects():
    for pyproject in sorted(PACKAGES.glob("*/pyproject.toml")):
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        yield pyproject.parent.name, data["project"]


def test_every_package_has_the_required_metadata():
    for name, project in _projects():
        assert project["requires-python"] == ">=3.10", name
        assert project["license"] == "MIT", name
        assert project["license-files"] == ["LICENSE"], name
        assert project["readme"] == "README.md", name
        assert set(project.get("urls", {})) == {"Homepage", "Issues", "Repository"}, name
        assert (PACKAGES / name / "LICENSE").exists(), name
        for key in ("description", "authors", "keywords", "classifiers"):
            assert project.get(key), f"{name}: missing {key}"


def test_every_tool_depends_on_a_compatible_gxcore():
    core = dict(_projects())["gxcore"]
    core_major_minor = tuple(int(x) for x in core["version"].split(".")[:2])
    for name, project in _projects():
        if name == "gxcore":
            continue
        dep = next((d for d in project.get("dependencies", []) if d.startswith("gxcore")), None)
        assert dep is not None, f"{name}: no gxcore dependency"
        match = re.match(r"gxcore>=(\d+)\.(\d+),<(\d+)\.(\d+)", dep)
        assert match, f"{name}: gxcore is not pinned to a range: {dep!r}"
        low = (int(match.group(1)), int(match.group(2)))
        high = (int(match.group(3)), int(match.group(4)))
        assert low <= core_major_minor < high, (
            f"{name}: gxcore {core['version']} is outside {dep!r}"
        )


def test_every_package_exposes_exactly_its_own_command():
    for name, project in _projects():
        scripts = sorted(project.get("scripts", {}))
        if name == "gxcore":
            assert scripts == [], name
        else:
            expected = "gxkit" if name == "gxkit" else name
            assert scripts == [expected], (
                f"{name}: expected the {expected!r} command, got {scripts}"
            )


def test_every_package_ships_a_py_typed_marker():
    for name, _ in _projects():
        marker = PACKAGES / name / "src" / name / "py.typed"
        assert marker.exists(), f"{name}: no src/{name}/py.typed"


def test_all_license_files_are_identical():
    root_license = (PACKAGES.parent / "LICENSE").read_text(encoding="utf-8")
    for name, _ in _projects():
        assert (PACKAGES / name / "LICENSE").read_text(encoding="utf-8") == root_license, name


def test_public_exports_resolve():
    import importlib

    for name, _ in _projects():
        module = importlib.import_module(name)
        for symbol in getattr(module, "__all__", []):
            assert hasattr(module, symbol), f"{name}.__all__ names missing {symbol!r}"
