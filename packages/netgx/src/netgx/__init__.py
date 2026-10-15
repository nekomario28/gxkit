"""netgx — inspect a network topology for segmentation and coherence faults.

Declare nodes with a kind and the allowed traffic between them; `netgx inspect`
finds an edge to an unknown node, a public entry that reaches sensitive data, a
self-loop, a duplicate edge, an isolated node, and a topology with no public
entry.
"""

from gxcore import ERROR, INFO, WARN, Problem, Report

from .checks import inspect_network
from .model import Network, load_network, network_from_parts
from .render import render_image
from .tool import TOOL, Scene, main

__all__ = [
    "ERROR",
    "INFO",
    "TOOL",
    "WARN",
    "Network",
    "Problem",
    "Report",
    "Scene",
    "inspect_network",
    "load_network",
    "main",
    "network_from_parts",
    "render_image",
]
__version__ = "1.0.0"
