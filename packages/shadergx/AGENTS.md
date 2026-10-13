# shadergx, for AI agents

A person pointed you here. `shadergx` renders a fragment shader headlessly and
checks the pixels, because you cannot see the shader you wrote.

Part of `gxkit`; the review contract (`inspect`, `--json`, exit codes,
storyboard) is shared with every other tool in the family.

## Set it up

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/shadergx" shadergx --help
uv tool install ./packages/shadergx
```

Needs a GL context (Mesa/EGL or a GPU). With none, `shadergx` says so.

## Write a shader

```python
import shadergx as s

shader = s.Shader(
    fragment="""
    uniform vec3 u_color;
    void main() {
        fragColor = vec4(uv * u_color.xy, 0.5, 1.0);
    }
    """,
    uniforms={"u_color": (0.4, 0.9, 0.0)},
    size=(256, 256),
)
```

The wrapper provides `#version 330 core`, the vertex shader, and `in vec2 uv`,
`uniform vec2 u_resolution`, `uniform float u_time`, `out vec4 fragColor`. Write
only `main` (and any custom `uniform` declarations). Or module-level `FRAGMENT`
/ `UNIFORMS` / `SIZE` / `TIME`.

## The loop

1. **Write** the shader as a `.py` file.
2. **Inspect** — `shadergx inspect shader.py`. It renders the shader, prints
   every problem with a stable `code`, and writes `<name>.storyboard.png` (the
   rendered image). **Exit 1 means at least one error.**
3. **Fix** and inspect again. Look at the storyboard: a black or flat image is
   the bug.
4. **Render** — `shadergx render shader.py -o shader.png`.

## Reading the report

- `error` — the shader does not work: `compile-error`, `bad-size`, `nan-output`,
  `black-output`. Exit code 1.
- `warn` — `constant-output` (ignores uv/inputs) or `uniform-unused` (a uniform
  you set changes nothing).
- `info` — `nondeterministic` (two identical renders differ).

Set every uniform you rely on and use `uv`/`u_time`; if a uniform is in the
report as unused, either use it or remove it.
