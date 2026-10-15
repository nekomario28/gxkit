"""flowgx — inspect state machines and flow charts for structural faults.

Declare a machine as data; `flowgx inspect` proves every state is reachable,
every state can still reach "done", and no event is ambiguous. Soft-locks in a
game level become "no way to finish" in a workflow — the same graph check.
"""

from gxcore import ERROR, INFO, WARN, Problem, Report

from .checks import inspect_machine
from .machine import Machine, load_machine, machine_from_parts
from .mermaid import diagram_in_markdown, machine_from_file, machine_from_mermaid
from .render import render_image
from .tool import TOOL, Scene, main

__all__ = [
    "ERROR",
    "INFO",
    "TOOL",
    "WARN",
    "Machine",
    "Problem",
    "Report",
    "Scene",
    "diagram_in_markdown",
    "inspect_machine",
    "load_machine",
    "machine_from_file",
    "machine_from_mermaid",
    "machine_from_parts",
    "main",
    "render_image",
]
__version__ = "1.0.0"
