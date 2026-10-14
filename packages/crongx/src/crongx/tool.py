"""Wire crongx into the shared CLI."""

from __future__ import annotations

from gxcore.toolkit import Scene, scene_tool

# `Scene` is part of this package's public surface; name it so a strict type
# checker sees the re-export instead of guessing.
__all__ = ["TOOL", "Scene", "main"]

from .checks import inspect_schedule
from .model import load_schedule
from .render import render_image

main, TOOL = scene_tool(
    name="crongx",
    description="Inspect a schedule of timed runs for overlaps on a shared resource, duplicate names and negative times.",
    load=load_schedule,
    inspect=inspect_schedule,
    to_image=render_image,
)
