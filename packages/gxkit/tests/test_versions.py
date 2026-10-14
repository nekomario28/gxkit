"""A version that drifts between pyproject, `__version__` and `--version` is a
dumb, preventable mistake. Keep the three in one place.

This test is the guard: it fails the moment they disagree.
"""

from __future__ import annotations

import importlib
import pathlib

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

PACKAGES = pathlib.Path(__file__).resolve().parents[2]


def _packages():
    for pyproject in sorted(PACKAGES.glob("*/pyproject.toml")):
        data = tomllib.loads(pyproject.read_text())
        yield pyproject.parent.name, data["project"]["name"], data["project"]["version"]


def test_every_package_declares_a_version():
    assert list(_packages()), "no packages found"


def test_pyproject_and_dunder_version_agree():
    for module_name, _, declared in _packages():
        module = importlib.import_module(module_name)
        assert module.__version__ == declared, (
            f"{module_name}: __version__ {module.__version__!r} != pyproject {declared!r}"
        )


def test_tool_version_matches_the_distribution():
    for module_name, _, declared in _packages():
        module = importlib.import_module(module_name)
        tool = getattr(module, "TOOL", None)
        if tool is not None:
            assert tool.version == declared, (
                f"{module_name}: TOOL.version {tool.version!r} != pyproject {declared!r}"
            )
