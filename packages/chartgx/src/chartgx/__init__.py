"""chartgx — inspect matplotlib charts for misleading or broken rendering.

A chart is a claim about data; a truncated axis turns 8% into 300%. `chartgx
inspect` reads the figure's artist tree, reports every problem with a stable
code and an exit code, and draws a storyboard with the problems outlined.
"""

from gxcore import ERROR, INFO, WARN, Problem, Report  # noqa: F401  (re-exported)

from .checks import inspect_figure
from .loader import load_figure
from .tool import Chart, TOOL, main

__all__ = [
    "inspect_figure",
    "load_figure",
    "Chart",
    "TOOL",
    "main",
    "Problem",
    "Report",
    "ERROR",
    "WARN",
    "INFO",
]
__version__ = "0.1.0"
