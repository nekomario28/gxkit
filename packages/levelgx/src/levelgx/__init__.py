"""levelgx — inspect game levels for reachability, solvability and soft-locks.

A level is a grid of characters. `levelgx inspect` flood-fills from the spawn,
proves the goal is solvable, finds stranded items, and — because one-way tiles
make the level directed — catches soft-locks: cells you can enter but never
leave with the goal still reachable.
"""

from gxcore import ERROR, INFO, WARN, Problem, Report

from .checks import can_reach, distances, inspect_level, reachable
from .level import Level, load_level
from .render import render_image
from .tool import TOOL, Scene, main

__all__ = [
    "ERROR",
    "INFO",
    "TOOL",
    "WARN",
    "Level",
    "Problem",
    "Report",
    "Scene",
    "can_reach",
    "distances",
    "inspect_level",
    "load_level",
    "main",
    "reachable",
    "render_image",
]
__version__ = "0.1.0"
