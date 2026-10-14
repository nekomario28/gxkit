"""Wire docgx into the shared CLI."""

from __future__ import annotations

from gxcore.toolkit import Scene, scene_tool

# `Scene` is part of this package's public surface; name it so a strict type
# checker sees the re-export instead of guessing.
__all__ = ["TOOL", "Scene", "main"]

from .checks import inspect_page
from .model import load_page
from .render import render_image

main, TOOL = scene_tool(
    name="docgx",
    description="Inspect a page / slide for overflowing, overlapping or unreadable text.",
    load=load_page,
    inspect=inspect_page,
    to_image=render_image,
)
