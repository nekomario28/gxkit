"""Wire framegx into the shared CLI."""

from __future__ import annotations

from gxcore.toolkit import Scene, scene_tool

# `Scene` is part of this package's public surface; name it so a strict type
# checker sees the re-export instead of guessing.
__all__ = ["TOOL", "Scene", "main"]

from .checks import inspect_video
from .clip import load_video
from .render import contact_sheet

main, TOOL = scene_tool(
    name="framegx",
    description="Inspect a rendered animation: black, frozen, wrong length, missing or silent sound.",
    load=load_video,
    inspect=inspect_video,
    to_image=contact_sheet,
    origin="top-left",
)
