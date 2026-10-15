"""gxkit — one entry point for the family.

An artifact goes in; the right `*gx` tool is chosen and run. See `gxkit tools`.

    from gxkit import detect, TOOLS
    from gxkit.cli import main
"""

from .cli import main
from .codes import CODEBOOK, flat, for_tool
from .registry import BY_NAME, TOOLS, ToolSpec, detect

__all__ = ["BY_NAME", "CODEBOOK", "TOOLS", "ToolSpec", "detect", "flat", "for_tool", "main"]
__version__ = "1.0.0"
