"""Wire netgx into the shared CLI."""

from __future__ import annotations

from gxcore.toolkit import Scene, scene_tool

# `Scene` is part of this package's public surface; name it so a strict type
# checker sees the re-export instead of guessing.
__all__ = ["TOOL", "Scene", "main"]

from .checks import inspect_network
from .model import load_network
from .render import render_image

main, TOOL = scene_tool(
    name="netgx",
    description="Inspect a network topology for dangling edges, public reach to sensitive data and self-loops.",
    load=load_network,
    inspect=inspect_network,
    to_image=render_image,
)
