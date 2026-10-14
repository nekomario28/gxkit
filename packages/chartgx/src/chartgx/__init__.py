"""chartgx — inspect matplotlib charts for misleading or broken rendering.

A chart is a claim about data; a truncated axis turns 8% into 300%. `chartgx
inspect` reads the figure's artist tree, reports every problem with a stable
code and an exit code, and draws a storyboard with the problems outlined.
"""

from gxcore import ERROR, INFO, WARN, Problem, Report

from .checks import inspect_figure
from .loader import load_figure
from .tool import TOOL, Chart, main

__all__ = [
    "ERROR",
    "INFO",
    "TOOL",
    "WARN",
    "Chart",
    "Problem",
    "Report",
    "inspect_figure",
    "load_figure",
    "main",
]
__version__ = "0.1.0"
