"""apigx — inspect an HTTP API contract for duplicates and unsafe mutations.

Declare endpoints and the base path; `apigx inspect` finds a route declared
twice, a state-changing method with no authentication, a path outside the
versioned base, an endpoint documenting no error, and deprecated routes.
"""

from gxcore import ERROR, INFO, WARN, Problem, Report

from .checks import inspect_api
from .model import API, Endpoint, api_from_parts, load_api
from .render import render_image
from .tool import TOOL, Scene, main

__all__ = [
    "API",
    "ERROR",
    "INFO",
    "TOOL",
    "WARN",
    "Endpoint",
    "Problem",
    "Report",
    "Scene",
    "api_from_parts",
    "inspect_api",
    "load_api",
    "main",
    "render_image",
]
__version__ = "0.1.0"
