"""gxkit — one entry point for the family.

An artifact goes in; the right `*gx` tool is chosen and run. See `gxkit tools`.

    from gxkit import detect, TOOLS
    from gxkit.cli import main
"""

from .registry import BY_NAME, TOOLS, ToolSpec, detect
from .cli import main

__all__ = ["TOOLS", "BY_NAME", "ToolSpec", "detect", "main"]
__version__ = "0.1.0"
