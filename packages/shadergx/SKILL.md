---
name: shadergx
description: Render a fragment shader headlessly and inspect the pixels before shipping it — a shader that fails to compile, outputs NaN/Inf, paints a single black or constant frame, or ignores a uniform the caller set. Write GLSL for a full-screen fragment shader; get stable codes, exit codes, and the rendered image as evidence. Use when writing or generating a GLSL / shader effect, procedural texture, or fragment shader you cannot see, and you need to prove it draws something and reacts to its inputs. Not for CPU rasterisation, and not for verifying a full renderer or engine.
---

# shadergx — see the shader you cannot see

Part of the `gxkit` family; the review contract is shared with every `*gx` tool.

## Install

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/shadergx" shadergx --help
uv tool install ./packages/shadergx
```

Needs a GL context (Mesa/EGL or a GPU); with none, the tool says so.

## Write a shader

The wrapper supplies `#version 330 core`, the full-screen vertex shader, and
`in vec2 uv`, `uniform vec2 u_resolution`, `uniform float u_time`,
`out vec4 fragColor`. Write only `main` and custom `uniform` declarations:

```python
import shadergx as s

shader = s.Shader(
    fragment="""
    uniform vec3 u_color;
    void main() { fragColor = vec4(uv * u_color.xy, 0.5, 1.0); }
    """,
    uniforms={"u_color": (0.4, 0.9, 0.0)},
    size=(256, 256),
)
```

Or module-level `FRAGMENT` / `UNIFORMS` / `SIZE` / `TIME`.

## The loop

1. Write the shader as a Python file.
2. `shadergx inspect shader.py` — renders, reports problems with stable `code`s,
   writes `<name>.storyboard.png` (the rendered image). **Exit 1 on any error.**
3. Fix and inspect again; look at the image (black or flat = the bug).
4. `shadergx render shader.py -o shader.png`.

## Severities

`error` = the shader does not work (`compile-error`, `nan-output`,
`black-output`). `warn` = it ignores its inputs (`constant-output`,
`uniform-unused`). `info` = non-deterministic.

## What it catches

| code | severity | meaning |
| --- | --- | --- |
| `compile-error` | error | the shader failed to compile or link |
| `bad-size` | error | the canvas is out of range (over 16M pixels) |
| `nan-output` | error | some pixels are NaN or Inf |
| `black-output` | error | one frame below the black level (mean RGB/alpha < 0.02) |
| `constant-output` | warn | one constant colour — ignores uv and inputs |
| `uniform-unused` | warn | a uniform is set but does not affect the output |
| `nondeterministic` | info | two identical-input renders differ |

The unused-uniform check is grounded in the GLSL compiler: if it removed the
uniform, the shader never reads it; if the uniform survives but changing it does
not move any pixel, the shader ignores it. Every check has a test that proves it
fires on a shader with the fault and stays quiet on one without (`tests/`).
