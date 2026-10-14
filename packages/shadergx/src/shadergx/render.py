"""Render a shader to a PIL image (the storyboard evidence)."""

from __future__ import annotations

from PIL import Image

from .gl import render_array, to_rgb8
from .model import Shader

__all__ = ["render_image"]


def render_image(shader: Shader) -> Image.Image:
    return to_rgb8(render_array(shader))
