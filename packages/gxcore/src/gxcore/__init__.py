"""gxcore — the shared review loop behind the `*gx` tools.

Turn an artifact into a report an agent can act on: problems with stable codes
and severities, an exit-code policy, a storyboard image, and a JSON form.

    from gxcore import Problem, Report, ERROR

Domain tools (`chartgx`, `levelgx`, …) add only a loader, a checks module, and
a renderer; the CLI, report and storyboard come from here.
"""

from .model import ERROR, INFO, WARN, SEVERITIES, BBox, Problem, Report
from .storyboard import annotate, safe_name, storyboard_path
from .report import human, to_json
from .cli import Tool, run

__all__ = [
    "ERROR",
    "WARN",
    "INFO",
    "SEVERITIES",
    "BBox",
    "Problem",
    "Report",
    "annotate",
    "safe_name",
    "storyboard_path",
    "human",
    "to_json",
    "Tool",
    "run",
]
__version__ = "0.1.0"
