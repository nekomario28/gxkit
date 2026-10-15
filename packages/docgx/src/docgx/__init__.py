"""docgx — inspect a page / slide for overflowing, overlapping or unreadable text.

Declare a title and positioned text blocks; `docgx inspect` measures the
rendered page and reports text that runs off the page, covers other text, is
too small to read, or breaks the page's budget.
"""

from gxcore import ERROR, INFO, WARN, Problem, Report

from .checks import inspect_page
from .model import Block, Page, load_page, page_from_parts
from .render import render_image
from .tool import TOOL, Scene, main

__all__ = [
    "ERROR",
    "INFO",
    "TOOL",
    "WARN",
    "Block",
    "Page",
    "Problem",
    "Report",
    "Scene",
    "inspect_page",
    "load_page",
    "main",
    "page_from_parts",
    "render_image",
]
__version__ = "1.0.0"
