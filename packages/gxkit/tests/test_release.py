"""The publish order must be dependency-first, and `--check` must catch a bad
`dist/`. Both are computed from the `pyproject` files; these pin the result.
"""

from __future__ import annotations

import importlib.util
import pathlib
import zipfile

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
    for _directory, name, _version, dependencies in module.projects():
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
    assert module.main([]) == 0
    out = capsys.readouterr().out
    assert "gxcore" in out and "uv publish" in out


def _wheel(tmp_path, module, name, version, *, include_py_typed=True):
    normalized = module._normalize(name)
    path = tmp_path / f"{normalized}-{version}-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{normalized}/licenses/LICENSE", "MIT")
        if include_py_typed:
            archive.writestr(f"{normalized}/py.typed", "")
    return path


def _fake_dist(tmp_path, module):
    for _directory, name, version, _deps in module.projects():
        _wheel(tmp_path, module, name, version)
        (tmp_path / f"{module._normalize(name)}-{version}.tar.gz").write_bytes(b"")
    return tmp_path


def test_check_dist_accepts_a_complete_dist(tmp_path):
    module = _release_module()
    _fake_dist(tmp_path, module)
    assert module.check_dist(tmp_path) == []
    assert module.main(["--check", str(tmp_path)]) == 0


def test_check_dist_reports_a_missing_wheel(tmp_path):
    module = _release_module()
    _fake_dist(tmp_path, module)
    (tmp_path / "gxcore-0.4.0-py3-none-any.whl").unlink()
    problems = module.check_dist(tmp_path)
    assert any("gxcore" in p and "no wheel" in p for p in problems)


def test_check_dist_reports_a_wrong_version(tmp_path):
    module = _release_module()
    _fake_dist(tmp_path, module)
    (tmp_path / "chartgx-0.1.0-py3-none-any.whl").rename(
        tmp_path / "chartgx-9.9.9-py3-none-any.whl"
    )
    assert any("chartgx" in p and "9.9.9" in p for p in module.check_dist(tmp_path))


def test_check_dist_reports_a_wheel_without_py_typed(tmp_path):
    module = _release_module()
    _fake_dist(tmp_path, module)
    (tmp_path / "docgx-0.1.0-py3-none-any.whl").unlink()
    _wheel(tmp_path, module, "docgx", "0.1.0", include_py_typed=False)
    assert any("docgx" in p and "py.typed" in p for p in module.check_dist(tmp_path))


def test_check_dist_reports_an_unexpected_wheel(tmp_path):
    module = _release_module()
    _fake_dist(tmp_path, module)
    _wheel(tmp_path, module, "ghostgx", "1.0.0")
    assert any("ghostgx" in p and "unexpected" in p for p in module.check_dist(tmp_path))
