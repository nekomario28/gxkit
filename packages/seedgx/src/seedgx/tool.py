"""Wire seedgx into the shared CLI."""

from __future__ import annotations

from gxcore.toolkit import Scene, scene_tool

# `Scene` is part of this package's public surface; name it so a strict type
# checker sees the re-export instead of guessing.
__all__ = ["TOOL", "Scene", "main"]

from .checks import inspect_spec
from .model import load_spec
from .render import render_image

main, TOOL = scene_tool(
    name="seedgx",
    description="Inspect a random-seed manifest for missing seeds, duplicate seeds and out-of-range values.",
    load=load_spec,
    inspect=inspect_spec,
    to_image=render_image,
)
