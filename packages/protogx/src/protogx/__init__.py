"""protogx — inspect a protocol state machine for deadlocks, unhandled messages
and unreachable states.

Declare states, transitions and the messages that drive them; `protogx inspect`
proves every state is reachable, that "done" is reachable from everywhere, and
that no declared message or awaited response is left unhandled.
"""

from gxcore import ERROR, INFO, WARN, Problem, Report  # noqa: F401  (re-exported)

from .checks import inspect_protocol
from .model import Protocol, load_protocol, protocol_from_parts
from .render import render_image
from .tool import TOOL, Scene, main

__all__ = [
    "Protocol",
    "load_protocol",
    "protocol_from_parts",
    "render_image",
    "inspect_protocol",
    "Scene",
    "TOOL",
    "main",
    "Problem",
    "Report",
    "ERROR",
    "WARN",
    "INFO",
]
__version__ = "0.1.0"
