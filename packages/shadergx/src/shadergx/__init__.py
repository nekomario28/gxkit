"""shadergx — render a fragment shader and inspect the pixels.

An agent writes a fragment shader it cannot see. `shadergx inspect` renders it
headlessly, reports a black/constant/NaN frame, and probes whether the uniforms
it set actually change anything.
"""

from gxcore import ERROR, INFO, WARN, Problem, Report  # noqa: F401  (re-exported)

from .checks import inspect_shader
from .gl import ShaderError, context, members, render_array
from .model import Shader, load_shader, shader_from_source
from .render import render_image
from .tool import TOOL, Scene, main

__all__ = [
    "Shader",
    "load_shader",
    "shader_from_source",
    "render_image",
    "inspect_shader",
    "render_array",
    "context",
    "members",
    "ShaderError",
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
