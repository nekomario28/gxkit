"""Wire flowgx into the shared CLI."""

from __future__ import annotations

from gxcore.toolkit import Scene, scene_tool  # noqa: F401  (Scene re-exported)

from .checks import inspect_machine
from .machine import load_machine
from .render import render_image

main, TOOL = scene_tool(
    name="flowgx",
    description="Inspect state machines / flow charts for unreachable, stuck and non-deterministic states.",
    load=load_machine,
    inspect=inspect_machine,
    to_image=render_image,
)
