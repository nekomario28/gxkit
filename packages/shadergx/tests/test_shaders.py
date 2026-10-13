"""Prove every shadergx check fires on a shader that has the fault.

These tests render on the GPU (or Mesa's software path); they skip where no GL
context can be created, so CI without a GPU stays green.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gxcore import ERROR, WARN
from gxcore.testing import assert_fires, assert_quiet

pytest.importorskip("moderngl")

from shadergx import Shader, inspect_shader, load_shader
from shadergx.gl import ShaderError, context


@pytest.fixture(autouse=True)
def _need_gl():
    try:
        context()
    except ShaderError as exc:
        pytest.skip(f"no GL context: {exc}")


def shader(fragment, **kw):
    return Shader(fragment=fragment, size=(64, 64), **kw)


def test_good_shader_has_no_errors():
    s = shader("void main(){ fragColor = vec4(uv, 0.5, 1.0); }")
    assert inspect_shader(s).errors == 0


def test_compile_error():
    s = shader("void main(){ fragColor = nope; }")
    assert_fires(inspect_shader(s), "compile-error", ERROR)


def test_black_output():
    s = shader("void main(){ fragColor = vec4(0.0, 0.0, 0.0, 1.0); }")
    assert_fires(inspect_shader(s), "black-output", ERROR)


def test_constant_output():
    s = shader("void main(){ fragColor = vec4(0.8, 0.2, 0.2, 1.0); }")
    assert_fires(inspect_shader(s), "constant-output", WARN)


def test_nan_output():
    s = shader("void main(){ fragColor = vec4(sqrt(-1.0)); }")
    assert_fires(inspect_shader(s), "nan-output", ERROR)


def test_unused_uniform_is_removed_by_the_compiler():
    s = shader("uniform vec3 u_tint;\nvoid main(){ fragColor = vec4(uv, 0.5, 1.0); }",
               uniforms={"u_tint": (1.0, 0.0, 0.0)})
    assert_fires(inspect_shader(s), "uniform-unused", WARN)


def test_used_uniform_is_quiet():
    s = shader("uniform vec3 u_tint;\nvoid main(){ fragColor = vec4(uv * u_tint.xy, 0.5, 1.0); }",
               uniforms={"u_tint": (1.0, 1.0, 0.0)})
    assert_quiet(inspect_shader(s), "uniform-unused")


def test_a_varying_shader_is_not_constant():
    s = shader("void main(){ fragColor = vec4(uv, 0.5, 1.0); }")
    assert_quiet(inspect_shader(s), "constant-output")


def test_examples_load_and_are_diagnosed():
    examples = Path(__file__).resolve().parents[1] / "examples"
    good, _ = load_shader(examples / "good_shader.py")
    broken, _ = load_shader(examples / "broken_shader.py")
    invalid, _ = load_shader(examples / "invalid_shader.py")
    assert inspect_shader(good).errors == 0
    assert_fires(inspect_shader(broken), "black-output", ERROR)
    assert_fires(inspect_shader(broken), "uniform-unused", WARN)
    assert_fires(inspect_shader(invalid), "compile-error", ERROR)
