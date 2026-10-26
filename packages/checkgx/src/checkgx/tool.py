"""Wire checkgx into the shared CLI."""

from __future__ import annotations

from gxcore.toolkit import Scene, scene_tool

__all__ = ["TOOL", "Scene", "main"]

from .checks import inspect_registry
from .model import load_registry
from .render import render_image

main, TOOL = scene_tool(
    name="checkgx",
    description="Inspect a check registry for duplicates, checks that are never evaluated, and checks sitting in metadata.",
    load=load_registry,
    inspect=inspect_registry,
    to_image=render_image,
)
