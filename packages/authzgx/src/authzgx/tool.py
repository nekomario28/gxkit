"""Wire authzgx into the shared CLI."""

from __future__ import annotations

from gxcore.toolkit import Scene, scene_tool  # noqa: F401  (Scene re-exported)

from .checks import inspect_auth
from .authmodel import load_model
from .render import render_image

main, TOOL = scene_tool(
    name="authzgx",
    description="Inspect permission models for privilege-escalation paths, cycles and dead config.",
    load=load_model,
    inspect=inspect_auth,
    to_image=render_image,
)
