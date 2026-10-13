"""schemagx — inspect a relational schema for dangling keys, cycles and dead tables.

Declare tables, primary keys and foreign keys; `schemagx inspect` checks every
reference resolves, finds foreign-key cycles that need deferred constraints, and
points at tables nothing uses.
"""

from gxcore import ERROR, INFO, WARN, Problem, Report  # noqa: F401  (re-exported)

from .checks import inspect_schema
from .model import Schema, load_schema, schema_from_parts
from .render import render_image
from .tool import TOOL, Scene, main

__all__ = [
    "Schema",
    "load_schema",
    "schema_from_parts",
    "render_image",
    "inspect_schema",
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
