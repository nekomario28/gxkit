"""seedgx — inspect a random-seed manifest for reproducibility.

Declare one seed per randomness stream; `seedgx inspect` finds a stream with no
seed, a seed outside the 32-bit range, two streams sharing a seed, a duplicate
stream, and a manifest marked non-deterministic.
"""

from gxcore import ERROR, INFO, WARN, Problem, Report

from .checks import inspect_spec
from .model import SeedSpec, Stream, load_spec, spec_from_parts
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
    "SeedSpec",
    "Stream",
    "inspect_spec",
    "load_spec",
    "main",
    "render_image",
    "spec_from_parts",
]
__version__ = "0.1.0"
