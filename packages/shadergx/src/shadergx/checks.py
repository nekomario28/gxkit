"""shadergx's domain knowledge: does the shader actually draw what it claims?

An agent cannot see a shader's output, so the checks look at the pixels: is the
frame black, constant, NaN? And do the uniforms the agent set actually change
anything? The GLSL compiler removing an unused uniform is the cheapest signal.
"""

from __future__ import annotations

import numpy as np

from gxcore import ERROR, INFO, WARN, Problem, Report

from .gl import ShaderError, members, perturb, render_array
from .model import Shader

_EPS = 1e-4
_MAX_PIXELS = 16_000_000


def _compact(text: str) -> str:
    """One readable line from a multi-line compiler log."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    pick = next((ln for ln in lines if "error" in ln.lower()), lines[0] if lines else "shader failed")
    return pick[:300]


def inspect_shader(shader: Shader, name: str | None = None) -> Report:
    name = name or shader.name
    width, height = shader.size
    report = Report(
        name=name,
        subject=f"shader: {width}x{height}",
        details=[f"{width}x{height}, {len(shader.uniforms)} uniforms"],
    )
    out: list[Problem] = []

    if width <= 0 or height <= 0 or width * height > _MAX_PIXELS:
        out.append(Problem(ERROR, "bad-size",
                           f"canvas {width}x{height} is out of range (1..{_MAX_PIXELS:,} pixels)"))
        report.problems = out
        return report

    try:
        base = render_array(shader)
    except ShaderError as exc:
        out.append(Problem(ERROR, "compile-error", _compact(str(exc))))
        report.problems = out
        return report

    if not np.isfinite(base).all():
        bad = int((~np.isfinite(base)).any(axis=-1).sum())
        out.append(Problem(ERROR, "nan-output",
                           f"{bad} pixel(s) are NaN or Inf — the output is undefined"))

    finite = np.nan_to_num(base)
    flat = finite.reshape(-1, finite.shape[-1])
    spread = float(np.ptp(flat, axis=0).max())

    if spread < _EPS:
        mean_rgb = float(flat[:, :3].mean())
        mean_alpha = float(flat[:, 3].mean())
        # Nothing visible: a black frame (opaque or not) or a fully transparent one.
        if mean_rgb < 0.02 or mean_alpha < 0.02:
            out.append(Problem(ERROR, "black-output",
                               "the shader paints a single black/transparent frame — nothing "
                               "visible is drawn"))
        else:
            out.append(Problem(WARN, "constant-output",
                               "the shader paints one constant colour — it ignores uv and its "
                               "inputs"))
    else:
        report.details.append("output varies across the frame")

    try:
        again = np.nan_to_num(render_array(shader))
        if again.shape == finite.shape and float(np.abs(finite - again).max()) > _EPS:
            out.append(Problem(INFO, "nondeterministic",
                               "two renders with identical inputs differ — the shader is not "
                               "deterministic"))
    except ShaderError:
        pass

    kept = set(members(shader))
    for key in shader.uniforms:
        if key in ("u_time", "u_resolution"):
            continue
        if key not in kept:
            out.append(Problem(WARN, "uniform-unused",
                               f"uniform {key!r} is set but the compiler removed it — the shader "
                               "never reads it"))

    if spread >= _EPS:
        for key in list(shader.uniforms)[:8]:
            if key in ("u_time", "u_resolution") or key not in kept:
                continue
            try:
                probe = np.nan_to_num(render_array(shader, overrides={key: perturb(shader.uniforms[key])}))
            except ShaderError:
                continue
            if probe.shape == finite.shape and float(np.abs(finite - probe).max()) < _EPS:
                out.append(Problem(WARN, "uniform-unused",
                                   f"changing {key!r} does not change the output — the shader "
                                   "ignores it"))

    report.problems = out
    return report
