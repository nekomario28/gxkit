"""flowgx — inspect state machines and flow charts for structural faults.

Declare a machine as data; `flowgx inspect` proves every state is reachable,
every state can still reach "done", and no event is ambiguous. Soft-locks in a
game level become "no way to finish" in a workflow — the same graph check.
"""

from gxcore import ERROR, INFO, WARN, Problem, Report  # noqa: F401  (re-exported)

from .checks import inspect_machine
from .machine import Machine, load_machine, machine_from_parts
from .render import render_image
from .tool import TOOL, Scene, main

__all__ = [
    "Machine",
    "load_machine",
    "machine_from_parts",
    "render_image",
    "inspect_machine",
    "Scene",
    "TOOL",
    "main",
    "Problem",
    "Report",
    "ERROR",
    "WARN",
    "INFO",
]
__version__ = "0.1.0"
