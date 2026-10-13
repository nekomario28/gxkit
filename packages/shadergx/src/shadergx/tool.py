"""Wire shadergx into the shared CLI."""

from __future__ import annotations

from gxcore.toolkit import Scene, scene_tool  # noqa: F401  (Scene re-exported)

from .checks import inspect_shader
from .model import load_shader
from .render import render_image

main, TOOL = scene_tool(
    name="shadergx",
    description="Render a fragment shader and inspect the pixels: black, constant, NaN, unused uniforms.",
    load=load_shader,
    inspect=inspect_shader,
    to_image=render_image,
)
