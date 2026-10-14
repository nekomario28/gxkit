"""gxcore — the shared review loop behind the `*gx` tools.

Turn an artifact into a report an agent can act on: problems with stable codes
and severities, an exit-code policy, a storyboard image, and a JSON form.

    from gxcore import Problem, Report, ERROR

Domain tools (`chartgx`, `levelgx`, `flowgx`, …) add only a loader, a checks
module, and a renderer; the CLI, report and storyboard come from here.
"""

from .cli import Tool, run
from .config import Config
from .config import apply as apply_config
from .config import load as load_config
from .graph import (
    can_reach,
    distances,
    find_cycle,
    reachable,
    reverse,
    shortest_path,
    strongly_connected_components,
    terminals,
    topological_sort,
    traps,
    unreachable,
    weak_components,
)
from .layout import TextBox
from .loading import load_from_file, load_module, resolve
from .model import ERROR, INFO, SEVERITIES, WARN, BBox, Problem, Report
from .report import human, to_json
from .storyboard import annotate, safe_name, storyboard_path

__all__ = [
    "ERROR",
    "INFO",
    "SEVERITIES",
    "WARN",
    "BBox",
    "Config",
    "Problem",
    "Report",
    "TextBox",
    "Tool",
    "annotate",
    "apply_config",
    "can_reach",
    "distances",
    "find_cycle",
    "human",
    "load_config",
    "load_from_file",
    "load_module",
    "reachable",
    "resolve",
    "reverse",
    "run",
    "safe_name",
    "shortest_path",
    "storyboard_path",
    "strongly_connected_components",
    "terminals",
    "to_json",
    "topological_sort",
    "traps",
    "unreachable",
    "weak_components",
]
__version__ = "0.5.0"
