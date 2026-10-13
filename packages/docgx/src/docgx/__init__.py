"""docgx — inspect a page / slide for overflowing, overlapping or unreadable text.

Declare a title and positioned text blocks; `docgx inspect` measures the
rendered page and reports text that runs off the page, covers other text, is
too small to read, or breaks the page's budget.
"""

from gxcore import ERROR, INFO, WARN, Problem, Report  # noqa: F401  (re-exported)

from .checks import inspect_page
from .model import Block, Page, load_page, page_from_parts
from .render import render_image
from .tool import TOOL, Scene, main

__all__ = [
    "Page",
    "Block",
    "load_page",
    "page_from_parts",
    "render_image",
    "inspect_page",
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
