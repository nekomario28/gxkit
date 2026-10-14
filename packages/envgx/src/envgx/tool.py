"""Wire envgx into the shared CLI."""

from __future__ import annotations

from gxcore.toolkit import Scene, scene_tool

# `Scene` is part of this package's public surface; name it so a strict type
# checker sees the re-export instead of guessing.
__all__ = ["TOOL", "Scene", "main"]

from .checks import inspect_environment
from .model import load_environment
from .render import render_image

main, TOOL = scene_tool(
    name="envgx",
    description="Inspect an environment/config declaration for undeclared references, secret defaults and type mistakes.",
    load=load_environment,
    inspect=inspect_environment,
    to_image=render_image,
)
