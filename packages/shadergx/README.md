# shadergx

**Render a fragment shader and inspect the pixels.** An agent writes a shader it
cannot see; `shadergx inspect` renders it headlessly (moderngl + EGL), reports a
black, constant or NaN frame, and probes whether the uniforms it set actually
change anything. The rendered image is the storyboard evidence.

One of the [`gxkit`](../../README.md) tools, built on [`gxcore`](../gxcore).

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/shadergx" shadergx inspect shader.py
# local:  uvx --from ../../packages/shadergx shadergx inspect shader.py
```

Needs a GL context: Mesa/EGL (or a GPU). With none, the tool says so instead of
guessing.

## Writing a shader

The wrapper supplies `#version 330 core`, the full-screen vertex shader and the
common inputs, so you write only `main` and any custom `uniform`s:

```python
import shadergx as s

shader = s.Shader(
    fragment="""
    uniform vec3 u_color;
    void main() {
        vec2 p = uv * 2.0 - 1.0;
        float v = 0.5 + 0.5 * sin(6.0 * length(p) - 2.0 * u_time);
        fragColor = vec4(u_color * v, 1.0);
    }
    """,
    uniforms={"u_color": (0.3, 0.7, 1.0)},
    size=(256, 256),
    time=0.8,
)
```

Provided to every shader: `in vec2 uv` (0..1), `uniform vec2 u_resolution`,
`uniform float u_time`, `out vec4 fragColor`. A source containing `#version` is
used verbatim.

## The contract

```
$ shadergx inspect broken_shader.py
broken_shader.py: Black frame
shader: 128x128
storyboard: Black_frame.storyboard.png
  128x128, 1 uniforms
inspect: 2 problems (1 error)
  [1] error black-output: the shader paints a single black/transparent frame — nothing visible is drawn
  [2] warn  uniform-unused: uniform 'u_color' is set but the compiler removed it — the shader never reads it
```

- **Exit code 1** when any `error`-severity problem is found.
- `--json` prints the same report machine-readably; `--no-storyboard` skips the
  image; `-o name.png` names it.

## Checks

| code | severity | what it means |
| --- | --- | --- |
| `compile-error` | error | the shader failed to compile or link |
| `bad-size` | error | the canvas is out of range (over 16M pixels) |
| `nan-output` | error | some pixels are NaN or Inf |
| `black-output` | error | a single fully-transparent/black frame — nothing drawn |
| `constant-output` | warn | one constant colour — the shader ignores uv and inputs |
| `uniform-unused` | warn | a uniform is set but does not affect the output |
| `nondeterministic` | info | two identical-input renders differ |

## Why it can be trusted

Every check is proven to fire on a shader with the fault and to stay quiet on one
without (`tests/`). The unused-uniform check is grounded in the GLSL compiler:
if it removed the uniform, the shader never reads it; if the uniform survives but
changing it does not change the pixels, the shader ignores it.

MIT licensed.
