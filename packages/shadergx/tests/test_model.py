"""`Shader.assembled` needs no GL: it is the string the compiler will see.

The wrapper injects the version, the common inputs and the output only when the
source lacks them — and must not be fooled into "verbatim" mode by a `#version`
that appears inside a comment.
"""

from __future__ import annotations

from shadergx.model import PREAMBLE, Shader, shader_from_source

COMMON = (
    "uniform vec2 u_resolution;",
    "uniform float u_time;",
    "in vec2 uv;",
    "out vec4 fragColor;",
)


def test_assembled_injects_preamble_and_common_inputs():
    out = Shader(fragment="void main(){ fragColor = vec4(uv, 0.5, 1.0); }").assembled()
    assert out.startswith(PREAMBLE)
    for decl in COMMON:
        assert decl in out


def test_assembled_keeps_an_explicit_version_verbatim():
    frag = "#version 330 core\nvoid main(){ fragColor = vec4(1.0); }"
    assert Shader(fragment=frag).assembled() == frag


def test_assembled_does_not_mistake_a_comment_for_a_version():
    frag = "// tuned for #version 330\nvoid main(){ fragColor = vec4(uv, 0.5, 1.0); }"
    out = Shader(fragment=frag).assembled()
    assert out.startswith(PREAMBLE)
    assert "out vec4 fragColor;" in out


def test_assembled_injects_only_missing_declarations():
    frag = "in vec2 uv;\nvoid main(){ fragColor = vec4(uv, 0.5, 1.0); }"
    out = Shader(fragment=frag).assembled()
    assert out.count("in vec2 uv;") == 1
    assert "uniform float u_time;" in out


def test_shader_from_source_sets_name_and_defaults():
    s = shader_from_source("void main(){}", name="x")
    assert s.name == "x"
    assert s.size == (256, 256)
    assert s.uniforms == {}
