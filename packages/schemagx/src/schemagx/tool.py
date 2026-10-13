"""Wire schemagx into the shared CLI."""

from __future__ import annotations

from gxcore.toolkit import Scene, scene_tool  # noqa: F401  (Scene re-exported)

from .checks import inspect_schema
from .model import load_schema
from .render import render_image

main, TOOL = scene_tool(
    name="schemagx",
    description="Inspect a relational schema for dangling keys, foreign-key cycles and dead tables.",
    load=load_schema,
    inspect=inspect_schema,
    to_image=render_image,
)
