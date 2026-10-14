"""shadergx check branches reached by patching the render boundary (no GL)."""

from __future__ import annotations

import numpy as np
import shadergx.checks as checks
from gxcore import INFO
from gxcore.testing import assert_fires
from shadergx import Shader, inspect_shader
from shadergx.gl import ShaderError


def _shader(**kw):
    return Shader(fragment="void main(){}", size=(4, 4), **kw)


def test_a_nondeterministic_shader_is_reported(monkeypatch):
    calls = {"n": 0}

    def fake_render(shader, **kw):
        calls["n"] += 1
        return np.full((2, 2, 4), float(calls["n"] % 2), dtype="f4")

    monkeypatch.setattr(checks, "render_array", fake_render)
    monkeypatch.setattr(checks, "members", lambda shader: [])
    report = inspect_shader(_shader(uniforms={"u_time": 1.0}))
    assert_fires(report, "nondeterministic", INFO)


def test_a_second_render_that_raises_is_ignored(monkeypatch):
    calls = {"n": 0}

    def fake_render(shader, **kw):
        calls["n"] += 1
        if calls["n"] > 1:
            raise ShaderError("boom")
        return np.zeros((2, 2, 4), dtype="f4")

    monkeypatch.setattr(checks, "render_array", fake_render)
    monkeypatch.setattr(checks, "members", lambda shader: [])
    assert isinstance(inspect_shader(_shader()).problems, list)


def test_a_failing_perturbing_render_is_ignored(monkeypatch):
    base = np.zeros((4, 4, 4), dtype="f4")
    base[0, 0, 0] = 1.0  # varies, so the perturbation probe runs

    def fake_render(shader, *, overrides=None, **kw):
        if overrides:
            raise ShaderError("boom")
        return base

    monkeypatch.setattr(checks, "render_array", fake_render)
    monkeypatch.setattr(checks, "members", lambda shader: ["u_x"])
    assert isinstance(inspect_shader(_shader(uniforms={"u_x": 0.0})).problems, list)
