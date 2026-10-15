"""crongx — inspect a schedule of timed runs for collisions.

Declare runs with a start, a duration and the resource they hold; `crongx inspect`
finds two runs that hold the same resource at once, a duplicate run, a negative
start or duration, and a run that never runs.
"""

from gxcore import ERROR, INFO, Problem, Report

from .checks import inspect_schedule
from .model import Run, Schedule, load_schedule, schedule_from_parts
from .render import render_image
from .tool import TOOL, Scene, main

__all__ = [
    "ERROR",
    "INFO",
    "TOOL",
    "Problem",
    "Report",
    "Run",
    "Scene",
    "Schedule",
    "inspect_schedule",
    "load_schedule",
    "main",
    "render_image",
    "schedule_from_parts",
]
__version__ = "1.0.0"
