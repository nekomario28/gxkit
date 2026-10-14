"""authzgx — inspect permission models for privilege-escalation paths.

Declare principals, roles, permissions and how they connect; `authzgx inspect`
computes what each principal can reach and proves whether a low-privilege
principal can reach a sensitive permission — a path, not a guess.
"""

from gxcore import ERROR, INFO, WARN, Problem, Report

from .authmodel import AuthModel, auth_from_parts, load_model
from .checks import inspect_auth
from .render import render_image
from .tool import TOOL, Scene, main

__all__ = [
    "ERROR",
    "INFO",
    "TOOL",
    "WARN",
    "AuthModel",
    "Problem",
    "Report",
    "Scene",
    "auth_from_parts",
    "inspect_auth",
    "load_model",
    "main",
    "render_image",
]
__version__ = "0.1.0"
