"""gxcore — the shared review loop behind the `*gx` tools.

Turn an artifact into a report an agent can act on: problems with stable codes
and severities, an exit-code policy, a storyboard image, and a JSON form.

    from gxcore import Problem, Report, ERROR

Domain tools (`chartgx`, `levelgx`, `flowgx`, …) add only a loader, a checks
module, and a renderer; the CLI, report and storyboard come from here.
"""

from .model import ERROR, INFO, WARN, SEVERITIES, BBox, Problem, Report
from .storyboard import annotate, safe_name, storyboard_path
from .report import human, to_json
from .cli import Tool, run
from .graph import can_reach, distances, find_cycle, reachable, reverse, shortest_path, terminals, traps, unreachable, weak_components
from .layout import TextBox
from .loading import load_from_file, load_module, resolve
from .config import Config, apply as apply_config, load as load_config

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
    "reachable",
    "reverse",
    "can_reach",
    "distances",
    "shortest_path",
    "traps",
    "unreachable",
    "terminals",
    "weak_components",
    "find_cycle",
    "TextBox",
    "load_from_file",
    "load_module",
    "resolve",
    "Config",
    "load_config",
    "apply_config",
]
__version__ = "0.4.0"
