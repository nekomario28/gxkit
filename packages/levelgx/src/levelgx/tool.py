"""Wire levelgx into the shared CLI."""

from __future__ import annotations

from gxcore.toolkit import Scene, scene_tool  # noqa: F401  (Scene re-exported)

from .checks import inspect_level
from .level import load_level
from .render import render_image

main, TOOL = scene_tool(
    name="levelgx",
    description="Inspect game levels for reachability, solvability and soft-locks.",
    load=load_level,
    inspect=inspect_level,
    to_image=render_image,
)
