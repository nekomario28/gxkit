"""Wire docgx into the shared CLI."""

from __future__ import annotations

from gxcore.toolkit import Scene, scene_tool  # noqa: F401  (Scene re-exported)

from .checks import inspect_page
from .model import load_page
from .render import render_image

main, TOOL = scene_tool(
    name="docgx",
    description="Inspect a page / slide for overflowing, overlapping or unreadable text.",
    load=load_page,
    inspect=inspect_page,
    to_image=render_image,
)
