"""depsgx — inspect a module dependency graph for cycles, layer violations and dead code.

Declare modules and what they depend on; `depsgx inspect` proves the graph is
acyclic, that no dependency points upward through the layers, and that nothing
is unreachable from the entry points.
"""

from gxcore import ERROR, INFO, WARN, Problem, Report

from .checks import inspect_graph
from .model import ModuleGraph, load_graph, modules_from_parts
from .render import render_image
from .tool import TOOL, Scene, main

__all__ = [
    "ERROR",
    "INFO",
    "TOOL",
    "WARN",
    "ModuleGraph",
    "Problem",
    "Report",
    "Scene",
    "inspect_graph",
    "load_graph",
    "main",
    "modules_from_parts",
    "render_image",
]
__version__ = "0.1.0"
