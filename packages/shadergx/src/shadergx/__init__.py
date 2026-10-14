"""shadergx — render a fragment shader and inspect the pixels.

An agent writes a fragment shader it cannot see. `shadergx inspect` renders it
headlessly, reports a black/constant/NaN frame, and probes whether the uniforms
it set actually change anything.
"""

from gxcore import ERROR, INFO, WARN, Problem, Report

from .checks import inspect_shader
from .gl import ShaderError, context, members, render_array
from .model import Shader, load_shader, shader_from_source
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
    "Shader",
    "ShaderError",
    "context",
    "inspect_shader",
    "load_shader",
    "main",
    "members",
    "render_array",
    "render_image",
    "shader_from_source",
]
__version__ = "0.1.0"
