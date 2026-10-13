"""A shader that does not compile — `shadergx` reports the compiler error."""

import shadergx as s

NAME = "Won't compile"

shader = s.Shader(
    fragment="""
void main() {
    fragColor = nope;   // undefined identifier
}
""",
    size=(64, 64),
)
