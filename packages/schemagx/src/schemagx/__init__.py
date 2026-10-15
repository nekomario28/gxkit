"""schemagx — inspect a relational schema for dangling keys, cycles and dead tables.

Declare tables, primary keys and foreign keys; `schemagx inspect` checks every
reference resolves, finds foreign-key cycles that need deferred constraints, and
points at tables nothing uses.
"""

from gxcore import ERROR, INFO, WARN, Problem, Report

from .checks import inspect_schema
from .ddl import schema_from_ddl, schema_from_file
from .model import Schema, load_schema, schema_from_parts, type_family
from .render import render_image
from .tool import TOOL, Scene, main

__all__ = [
    "ERROR",
    "INFO",
    "TOOL",
    "WARN",
    "Problem",
    "Report",
    "Scene",
    "Schema",
    "inspect_schema",
    "load_schema",
    "main",
    "render_image",
    "schema_from_ddl",
    "schema_from_file",
    "schema_from_parts",
    "type_family",
]
__version__ = "0.1.0"
