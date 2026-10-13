"""authzgx — inspect permission models for privilege-escalation paths.

Declare principals, roles, permissions and how they connect; `authzgx inspect`
computes what each principal can reach and proves whether a low-privilege
principal can reach a sensitive permission — a path, not a guess.
"""

from gxcore import ERROR, INFO, WARN, Problem, Report  # noqa: F401  (re-exported)

from .authmodel import AuthModel, auth_from_parts, load_model
from .checks import inspect_auth
from .render import render_image
from .tool import TOOL, Scene, main

__all__ = [
    "AuthModel",
    "load_model",
    "auth_from_parts",
    "render_image",
    "inspect_auth",
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
