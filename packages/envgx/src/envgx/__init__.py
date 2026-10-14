"""envgx — inspect an environment / configuration declaration for drift.

Declare variables and the names the code reads; `envgx inspect` finds a reference
to something undeclared, a declaration nothing reads, a secret that carries a
default, a type that is not real, and a required variable that also has a default.
"""

from gxcore import ERROR, INFO, WARN, Problem, Report

from .checks import inspect_environment
from .model import Environment, Variable, environment_from_parts, load_environment
from .render import render_image
from .tool import TOOL, Scene, main

__all__ = [
    "ERROR",
    "INFO",
    "TOOL",
    "WARN",
    "Environment",
    "Problem",
    "Report",
    "Scene",
    "Variable",
    "environment_from_parts",
    "inspect_environment",
    "load_environment",
    "main",
    "render_image",
]
__version__ = "0.1.1"
