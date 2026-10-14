"""Wire apigx into the shared CLI."""

from __future__ import annotations

from gxcore.toolkit import Scene, scene_tool

# `Scene` is part of this package's public surface; name it so a strict type
# checker sees the re-export instead of guessing.
__all__ = ["TOOL", "Scene", "main"]

from .checks import inspect_api
from .model import load_api
from .render import render_image

main, TOOL = scene_tool(
    name="apigx",
    description="Inspect an HTTP API contract for duplicate routes, unauthenticated mutations and unversioned paths.",
    load=load_api,
    inspect=inspect_api,
    to_image=render_image,
)
