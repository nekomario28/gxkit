"""protogx — inspect a protocol state machine for deadlocks, unhandled messages
and unreachable states.

Declare states, transitions and the messages that drive them; `protogx inspect`
proves every state is reachable, that "done" is reachable from everywhere, and
that no declared message or awaited response is left unhandled.
"""

from gxcore import ERROR, INFO, WARN, Problem, Report

from .checks import inspect_protocol
from .model import Protocol, load_protocol, protocol_from_parts
from .render import render_image
from .tool import TOOL, Scene, main

__all__ = [
    "ERROR",
    "INFO",
    "TOOL",
    "WARN",
    "Problem",
    "Protocol",
    "Report",
    "Scene",
    "inspect_protocol",
    "load_protocol",
    "main",
    "protocol_from_parts",
    "render_image",
]
__version__ = "1.0.0"
