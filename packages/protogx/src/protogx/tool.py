"""Wire protogx into the shared CLI."""

from __future__ import annotations

from gxcore.toolkit import Scene, scene_tool

# `Scene` is part of this package's public surface; name it so a strict type
# checker sees the re-export instead of guessing.
__all__ = ["TOOL", "Scene", "main"]

from .checks import inspect_protocol
from .model import load_protocol
from .render import render_image

main, TOOL = scene_tool(
    name="protogx",
    description="Inspect a protocol state machine for deadlocks, unhandled messages and unreachable states.",
    load=load_protocol,
    inspect=inspect_protocol,
    to_image=render_image,
)
