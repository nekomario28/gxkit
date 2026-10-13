"""Wire depsgx into the shared CLI."""

from __future__ import annotations

from gxcore.toolkit import Scene, scene_tool  # noqa: F401  (Scene re-exported)

from .checks import inspect_graph
from .model import load_graph
from .render import render_image

main, TOOL = scene_tool(
    name="depsgx",
    description="Inspect a module dependency graph for cycles, layer violations and dead code.",
    load=load_graph,
    inspect=inspect_graph,
    to_image=render_image,
)
