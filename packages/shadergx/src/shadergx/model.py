"""A fragment shader and the uniforms that drive it.

    import shadergx as s

    shader = s.Shader(
        fragment=\"\"\"
        uniform vec3 u_color;
        void main() {
            fragColor = vec4(uv, 0.5 + 0.5 * sin(u_time), 1.0);
        }
        \"\"\",
        uniforms={"u_color": (0.2, 0.4, 0.9)},
        size=(256, 256),
    )

The wrapper supplies the version, the full-screen vertex shader and the common
inputs (``uv``, ``u_resolution``, ``u_time``, ``fragColor``); the agent writes
only ``main`` and any custom ``uniform`` declarations. If the source contains
``#version`` it is used verbatim (then it must declare everything it uses).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

PREAMBLE = "#version 330 core"
# A real directive starts a line; `#version` inside a comment must not switch
# the shader to "verbatim" mode and silently drop the preamble.
_VERSION_DIRECTIVE = re.compile(r"^\s*#version\b", re.MULTILINE)


@dataclass
class Shader:
    fragment: str
    uniforms: dict[str, object] = field(default_factory=dict)
    size: tuple[int, int] = (256, 256)
    time: float = 0.0
    name: str = "shader"

    def assembled(self) -> str:
        src = self.fragment
        if _VERSION_DIRECTIVE.search(src):
            return src
        lines = [PREAMBLE]
        # Inject only what the source does not already declare (a *use* of
        # fragColor is not a declaration).
        if "uniform vec2 u_resolution" not in src:
            lines.append("uniform vec2 u_resolution;")
        if "uniform float u_time" not in src:
            lines.append("uniform float u_time;")
        if "in vec2 uv" not in src:
            lines.append("in vec2 uv;")
        if "out vec4 fragColor" not in src:
            lines.append("out vec4 fragColor;")
        return "\n".join(lines) + "\n" + src


def _as_shader(value: object) -> Shader | None:
    return value if isinstance(value, Shader) else None


def load_shader(path: str | Path) -> tuple[Shader, object]:
    from gxcore.loading import load_module, resolve

    path = Path(path)
    module = load_module(path)
    shader = resolve(
        module,
        attrs=("shader", "SHADER", "fragment", "FRAGMENT"),
        builders=("build", "make_shader", "make"),
        convert=_as_shader,
    )
    if shader is None:
        fragment = getattr(module, "FRAGMENT", getattr(module, "fragment", None))
        if isinstance(fragment, str):
            size = getattr(module, "SIZE", getattr(module, "size", (256, 256)))
            shader = Shader(
                fragment=fragment,
                uniforms=dict(getattr(module, "UNIFORMS", getattr(module, "uniforms", {}))),
                size=(int(size[0]), int(size[1])),
                time=float(getattr(module, "TIME", getattr(module, "time", 0.0))),
            )
    if shader is None:
        raise ValueError(
            f"{path}: no shader found — define `shader` (a Shader) or FRAGMENT (a string)"
        )
    if shader.name == "shader":
        shader.name = getattr(module, "NAME", path.stem)
    return shader, module


def shader_from_source(
    fragment: str,
    uniforms: dict[str, object] | None = None,
    size: tuple[int, int] = (256, 256),
    time: float = 0.0,
    name: str = "shader",
) -> Shader:
    return Shader(
        fragment=fragment,
        uniforms=dict(uniforms or {}),
        size=(int(size[0]), int(size[1])),
        time=time,
        name=name,
    )
