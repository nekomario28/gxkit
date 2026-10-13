"""Compile and render a fragment shader headlessly through moderngl + EGL.

The pixel readback is the ground truth the checks reason about. If no GL
context is available the tool says so plainly instead of guessing.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .model import Shader

VERTEX = """#version 330 core
in vec2 in_pos;
out vec2 uv;
void main() {
    uv = in_pos * 0.5 + 0.5;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""

_TRIANGLE = np.array([-1.0, -1.0, 3.0, -1.0, -1.0, 3.0], dtype="f4")

_ctx = None
_programs: dict[str, Any] = {}


class ShaderError(Exception):
    """The shader failed to compile, link, or could not be rendered."""


def context():
    global _ctx
    if _ctx is not None:
        return _ctx
    try:
        import moderngl
    except Exception as exc:  # pragma: no cover - import guard
        raise ShaderError(
            "moderngl is not installed — `pip install moderngl` (needs Mesa/EGL or a GPU)"
        ) from exc
    for backend in ("egl", "glx"):
        try:
            _ctx = moderngl.create_standalone_context(backend=backend)
            return _ctx
        except Exception:
            continue
    raise ShaderError(
        "no GL context available (tried egl and glx) — install Mesa/EGL or run "
        "somewhere with a GPU"
    )


def program(shader: Shader):
    """Compile (and cache) the shader's program."""
    src = shader.assembled()
    if src in _programs:
        return _programs[src]
    ctx = context()
    try:
        prog = ctx.program(vertex_shader=VERTEX, fragment_shader=src)
    except Exception as exc:
        raise ShaderError(str(exc) or "GLSL compiler/linker failed") from exc
    _programs[src] = prog
    return prog


def members(shader: Shader) -> list[str]:
    """Names the compiler kept (attributes and uniforms). Unused uniforms are
    optimised away, so a declared uniform missing here is an unused uniform."""
    return list(program(shader))


def _set(prog, name: str, value: object) -> bool:
    if name not in prog:
        return False
    try:
        prog[name].value = value
        return True
    except Exception:
        return False


def render_array(shader: Shader, *, time: float | None = None, overrides: dict[str, Any] | None = None) -> np.ndarray:
    """Render the shader and return an ``(H, W, 4)`` float32 array, top-left origin."""
    import moderngl

    prog = program(shader)
    ctx = context()
    width, height = shader.size

    texture = ctx.texture((width, height), 4, dtype="f4")
    fbo = ctx.framebuffer(color_attachments=[texture])
    fbo.use()
    ctx.clear(0.0, 0.0, 0.0, 0.0)
    vao = ctx.vertex_array(prog, [(ctx.buffer(_TRIANGLE), "2f", "in_pos")])

    _set(prog, "u_resolution", (float(width), float(height)))
    _set(prog, "u_time", float(shader.time if time is None else time))
    uniform_values: dict[str, Any] = dict(shader.uniforms)
    if overrides:
        uniform_values.update(overrides)
    for key, value in uniform_values.items():
        _set(prog, key, value)

    vao.render(moderngl.TRIANGLES, vertices=3)
    raw = fbo.read(components=4, dtype="f4")
    arr = np.frombuffer(raw, dtype="f4").reshape(height, width, 4)
    return arr[::-1]  # GL origin is bottom-left


def to_rgb8(arr: np.ndarray):
    """Clamp a float render to an 8-bit RGB PIL image."""
    from PIL import Image

    finite = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=0.0)
    rgb = np.clip(finite[..., :3], 0.0, 1.0)
    return Image.fromarray((rgb * 255.0 + 0.5).astype("uint8"), "RGB")


def perturb(value: object) -> object:
    """A nearby value for the same uniform type (for the unused-uniform probe)."""
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, float):
        return value + 0.37
    if isinstance(value, (list, tuple)):
        return tuple((v + 0.37) if isinstance(v, (int, float)) else v for v in value)
    return (0.37, 0.37, 0.37, 0.37)
