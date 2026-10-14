"""Wire chartgx's domain code into the shared CLI.

This is the whole cost of a new tool: a loader, a checks module, a renderer,
and a `gxcore.Tool`. The contract — `inspect`, `--json`, exit codes, storyboard,
`render` — comes from `gxcore`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gxcore import Tool, run
from gxcore.toolkit import distribution_version

from .checks import inspect_figure
from .loader import load_figure


@dataclass
class Chart:
    fig: Any
    path: Path
    name: str


def _figure_name(fig: Any, fallback: str) -> str:
    if fig.get_suptitle().strip():
        return fig.get_suptitle().strip()
    for ax in fig.axes:
        if ax.get_title().strip():
            return ax.get_title().strip()
    return fallback


def load(path: Path) -> Chart:
    fig, _ = load_figure(path)
    return Chart(fig=fig, path=Path(path), name=_figure_name(fig, Path(path).stem))


def inspect(chart: Chart):
    return inspect_figure(chart.fig, name=chart.name)


def render(chart: Chart, out: Path | None, dpi: float | None) -> Path:
    out = Path(out) if out else Path(f"{chart.path.stem}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    chart.fig.savefig(out, dpi=dpi, facecolor=chart.fig.get_facecolor())
    return out


def to_image(chart: Chart):
    from PIL import Image

    fig = chart.fig
    fig.canvas.draw()
    w, h = fig.canvas.get_width_height()
    return Image.frombytes("RGBA", (w, h), bytes(fig.canvas.buffer_rgba()))


TOOL = Tool(
    name="chartgx",
    description="Inspect matplotlib figures for misleading or broken charts.",
    load=load,
    inspect=inspect,
    render=render,
    to_image=to_image,
    version=distribution_version("chartgx"),
)


def main(argv: list[str] | None = None) -> int:
    return run(TOOL, argv)
