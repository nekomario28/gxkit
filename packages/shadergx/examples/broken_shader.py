"""A shader with faults.

  * it paints a single black frame                  -> black-output
  * the uniform u_color is never read               -> uniform-unused
"""

import shadergx as s

NAME = "Black frame"

shader = s.Shader(
    fragment="""
uniform vec3 u_color;
void main() {
    fragColor = vec4(0.0, 0.0, 0.0, 1.0);
}
""",
    uniforms={"u_color": (1.0, 0.0, 0.0)},
    size=(128, 128),
)
