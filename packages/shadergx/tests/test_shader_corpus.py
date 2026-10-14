"""A corpus of GLSL, not just the two example shaders.

An agent writing a shader cannot see it compile. If a construct an agent is
likely to reach for — a `for` loop, a `mat2` uniform, an array constructor —
produced a false `compile-error`, the tool would be lying about the language it
supports. Every valid shader here must link; every invalid one must surface a
`compile-error`. The point is coverage of the surface, driven by the pixels.
"""

from __future__ import annotations

import pytest

pytest.importorskip("moderngl")

from gxcore import ERROR
from gxcore.testing import assert_fires
from shadergx import Shader, inspect_shader
from shadergx.gl import ShaderError, context

VALID = {
    "varying_uv": "void main(){ fragColor = vec4(uv, 0.5, 1.0); }",
    "trig": "void main(){ float v=0.5+0.5*sin(uv.x*20.0)*cos(uv.y*20.0); fragColor=vec4(v,v,v,1.0); }",
    "length_pow": (
        "void main(){ vec2 p=uv*2.0-1.0; float v=pow(1.0-length(p),3.0); "
        "fragColor=vec4(v,0.2,0.4,1.0); }"
    ),
    "smoothstep_mix": (
        "void main(){ float v=smoothstep(0.2,0.8,uv.x); "
        "fragColor=mix(vec4(0.0,0.0,0.2,1.0), vec4(1.0,0.6,0.0,1.0), v); }"
    ),
    "fract_step_clamp": (
        "void main(){ float v=fract(uv.x*8.0); v=step(0.5,v); v=clamp(v,0.0,1.0); "
        "fragColor=vec4(vec3(v),1.0); }"
    ),
    "dot_normalize": (
        "void main(){ vec2 n=normalize(uv*2.0-1.0); "
        "fragColor=vec4(vec3(0.5+0.5*dot(n,vec2(0.7,0.7))),1.0); }"
    ),
    "loop_if": (
        "void main(){ vec3 c=vec3(0.0); for(int i=0;i<8;i++){ if(i%2==0){ c+=vec3(0.1); } } "
        "fragColor=vec4(c,1.0); }"
    ),
    "helper_function": (
        "float wave(vec2 p){ return 0.5+0.5*sin(p.x*10.0)*sin(p.y*10.0); } "
        "void main(){ fragColor=vec4(vec3(wave(uv)),1.0); }"
    ),
    "uniform_float": "uniform float u_gain; void main(){ fragColor=vec4(vec3(uv.x*u_gain),1.0); }",
    "uniform_vec2": "uniform vec2 u_scale; void main(){ fragColor=vec4(uv*u_scale,0.0,1.0); }",
    "uniform_vec3": ("uniform vec3 u_color; void main(){ fragColor=vec4(uv*u_color.xy,0.5,1.0); }"),
    "uniform_vec4": "uniform vec4 u_tint; void main(){ fragColor=vec4(uv,0.0,1.0)*u_tint; }",
    "uniform_int": (
        "uniform int u_steps; void main(){ fragColor=vec4(vec3(fract(uv.x*float(u_steps))),1.0); }"
    ),
    "uniform_bool": (
        "uniform bool u_invert; void main(){ float v=u_invert?1.0-uv.x:uv.x; "
        "fragColor=vec4(vec3(v),1.0); }"
    ),
    "uniform_mat2": "uniform mat2 u_m; void main(){ fragColor=vec4(uv*u_m,0.0,1.0); }",
    "time_anim": (
        "void main(){ float v=0.5+0.5*sin(6.2831*(uv.x-u_time)); fragColor=vec4(vec3(v),1.0); }"
    ),
    "resolution": (
        "void main(){ vec2 p=uv*u_resolution; fragColor=vec4(vec3(fract(p.x/32.0)),1.0); }"
    ),
    "const_array": (
        "void main(){ float w[4]=float[4](0.0,0.33,0.66,1.0); "
        "int i=int(clamp(floor(uv.x*4.0),0.0,3.0)); fragColor=vec4(vec3(w[i]),1.0); }"
    ),
    "while_loop": (
        "void main(){ float v=uv.x; int i=0; while(i<5){ v=fract(v*2.0); i++; } "
        "fragColor=vec4(vec3(v),1.0); }"
    ),
    "declares_common_inputs": (
        "uniform float u_time; in vec2 uv; out vec4 fragColor; "
        "void main(){ fragColor=vec4(uv,0.5,1.0); }"
    ),
    "explicit_version": (
        "#version 330 core\nuniform vec2 u_resolution; uniform float u_time; "
        "in vec2 uv; out vec4 fragColor;\nvoid main(){ fragColor=vec4(uv,0.5,1.0); }"
    ),
}

INVALID = {
    "undefined_symbol": "void main(){ fragColor = nope; }",
    "missing_semicolon": "void main(){ fragColor = vec4(1.0) }",
    "type_mismatch": "void main(){ float x = uv; fragColor = vec4(x); }",
    "undefined_function": "void main(){ fragColor = missing_fn(uv); }",
    "no_main": "float f(){ return 1.0; }",
    "bad_version": "#version 999 core\nvoid main(){ fragColor=vec4(1.0); }",
    "syntax_error": "void main( { fragColor = vec4(1.0); }",
    "redefinition": "void main(){ fragColor=vec4(1.0); } void main(){ fragColor=vec4(0.0); }",
}


@pytest.fixture(autouse=True)
def _need_gl():
    try:
        context()
    except ShaderError as exc:
        pytest.skip(f"no GL context: {exc}")


@pytest.mark.parametrize("name", sorted(VALID))
def test_valid_shader_compiles(name):
    report = inspect_shader(Shader(fragment=VALID[name], size=(64, 64)))
    compile_error = next((p for p in report.problems if p.code == "compile-error"), None)
    assert compile_error is None, f"{name}: {compile_error and compile_error.message}"


@pytest.mark.parametrize("name", sorted(INVALID))
def test_invalid_shader_reports_compile_error(name):
    report = inspect_shader(Shader(fragment=INVALID[name], size=(64, 64)))
    assert_fires(report, "compile-error", ERROR)
