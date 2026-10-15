"""pipegx — inspect a build pipeline DAG before you run it.

Declare steps with their needs and produced artifacts, and the goals the pipeline
must deliver; `pipegx inspect` finds a need that names no step, a cycle, a step
declared twice, an artifact produced twice, and a goal nothing produces.
"""

from gxcore import ERROR, INFO, Problem, Report

from .checks import inspect_pipeline
from .model import Pipeline, Step, load_pipeline, pipeline_from_parts
from .render import render_image
from .tool import TOOL, Scene, main

__all__ = [
    "ERROR",
    "INFO",
    "TOOL",
    "Pipeline",
    "Problem",
    "Report",
    "Scene",
    "Step",
    "inspect_pipeline",
    "load_pipeline",
    "main",
    "pipeline_from_parts",
    "render_image",
]
__version__ = "0.1.2"
