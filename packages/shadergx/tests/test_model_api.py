"""shadergx bits that need no GL: the loader fallback and `perturb`'s default."""

from __future__ import annotations

from shadergx.gl import perturb
from shadergx.model import load_shader, shader_from_source


def test_perturb_falls_back_for_a_value_it_does_not_understand():
    assert perturb("red") == (0.37, 0.37, 0.37, 0.37)
    assert perturb(None) == (0.37, 0.37, 0.37, 0.37)


def test_load_shader_accepts_a_bare_fragment_string(tmp_path):
    src = tmp_path / "s.py"
    src.write_text(
        "FRAGMENT = 'void main(){ fragColor = vec4(1.0); }'\n"
        "SIZE = (32, 32)\n"
        "UNIFORMS = {}\n"
        "NAME = 'bare'\n"
    )
    shader, _module = load_shader(src)
    assert shader.fragment.strip().startswith("void main")
    assert shader.size == (32, 32)
    assert shader.name == "bare"
    assert shader_from_source("x").size == (256, 256)
