"""Wire pipegx into the shared CLI."""

from __future__ import annotations

from gxcore.toolkit import Scene, scene_tool

# `Scene` is part of this package's public surface; name it so a strict type
# checker sees the re-export instead of guessing.
__all__ = ["TOOL", "Scene", "main"]

from .checks import inspect_pipeline
from .model import load_pipeline
from .render import render_image

main, TOOL = scene_tool(
    name="pipegx",
    description="Inspect a build pipeline DAG for unknown steps, cycles and unproduced goals.",
    load=load_pipeline,
    inspect=inspect_pipeline,
    to_image=render_image,
)
