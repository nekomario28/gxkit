"""The publish order must be dependency-first: a tool published before `gxcore`
cannot be installed, and the umbrella comes last. `scripts/release.py` computes it
from the `pyproject` files; these pin the result.
"""

from __future__ import annotations

import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]


def _release_module():
    path = ROOT / "scripts" / "release.py"
    spec = importlib.util.spec_from_file_location("release", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_publish_order_is_dependency_first():
    module = _release_module()
    order = module.publish_order()
    assert order, "the package graph has a cycle"
    assert order[0] == "gxcore", "gxcore must be published first"
    assert order[-1] == "gxkit-cli", "the umbrella must be published last"
    position = {name: i for i, name in enumerate(order)}
    for _directory, name, dependencies in module.projects():
        for dependency in module.internal(dependencies):
            assert position[dependency] < position[name], (
                f"{name} is published before its dependency {dependency}"
            )


def test_publish_order_covers_the_whole_family():
    from gxkit.registry import TOOLS

    module = _release_module()
    expected = {"gxcore", "gxkit-cli", *(t.name for t in TOOLS)}
    assert set(module.publish_order()) == expected


def test_release_reports_a_usable_plan(capsys):
    module = _release_module()
    assert module.main() == 0
    out = capsys.readouterr().out
    assert "gxcore" in out and "uv publish" in out
