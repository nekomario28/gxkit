"""A shader that should pass: it varies across the frame and uses its uniform."""

import shadergx as s

NAME = "Plasma"

shader = s.Shader(
    fragment="""
uniform vec3 u_color;
void main() {
    vec2 p = uv * 2.0 - 1.0;
    float r = length(p);
    float v = 0.5 + 0.5 * sin(6.0 * r - 2.0 * u_time);
    fragColor = vec4(u_color * v, 1.0);
}
""",
    uniforms={"u_color": (0.3, 0.7, 1.0)},
    size=(192, 192),
    time=0.8,
)
