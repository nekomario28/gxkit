"""Wire chartgx's domain code into the shared CLI.

This is the whole cost of a new tool: a loader, a checks module, a renderer,
and a `gxcore.Tool`. The contract — `inspect`, `--json`, exit codes, storyboard,
`render` — comes from `gxcore`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gxcore import Report, Tool, run
from gxcore.toolkit import distribution_version
from PIL import Image

from .checks import inspect_figure
from .loader import load_figure
from .model import inspect_model, load_model


@dataclass
class Chart:
    """A matplotlib figure, loaded by running the script that builds it."""

    fig: Any
    path: Path
    name: str


@dataclass
class Declared:
    """A chart declared as data: checked without matplotlib and without running it."""

    model: dict[str, Any]
    path: Path
    name: str


Artifact = Chart | Declared

#: A declaration is JSON; a figure is Python.
DECLARATION_SUFFIXES = (".json",)


def _figure_name(fig: Any, fallback: str) -> str:
    if fig.get_suptitle().strip():
        return str(fig.get_suptitle().strip())
    for ax in fig.axes:
        if ax.get_title().strip():
            return str(ax.get_title().strip())
    return fallback


def load(path: Path) -> Artifact:
    path = Path(path)
    if path.suffix.lower() in DECLARATION_SUFFIXES:
        model = load_model(path)
        title = model.get("title")
        name = str(title) if isinstance(title, str) and title.strip() else path.stem
        return Declared(model=model, path=path, name=name)
    fig, _ = load_figure(path)
    return Chart(fig=fig, path=path, name=_figure_name(fig, path.stem))


def inspect(artifact: Artifact) -> Report:
    if isinstance(artifact, Declared):
        return inspect_model(artifact.model, name=artifact.name)
    return inspect_figure(artifact.fig, name=artifact.name)


def render(artifact: Artifact, out: Path | None, dpi: float | None) -> Path:
    if isinstance(artifact, Declared):
        raise ValueError(
            "a declared model has no renderer here: chartgx draws matplotlib figures, "
            "and a figspec model is rendered by figspec. Inspect it instead"
        )
    out = Path(out) if out else Path(f"{artifact.path.stem}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    artifact.fig.savefig(out, dpi=dpi, facecolor=artifact.fig.get_facecolor())
    return out


def to_image(artifact: Artifact) -> Image.Image:
    from PIL import Image

    if isinstance(artifact, Declared):
        # The storyboard boxes a matplotlib figure's artists. A declaration has no
        # artists, so there is nothing to box — and printing a chart without boxes
        # while the report numbers findings would claim the two agree when they do
        # not. The report is still printed; only the image is skipped, with this
        # reason.
        raise ValueError(
            "a declared model has no storyboard here: box numbers are drawn over a "
            "matplotlib figure's artists, which a declaration does not have. The "
            "renderer that owns the model can draw one — `figspec storyboard "
            "model.json -o model.storyboard.svg` boxes the marks these findings name"
        )
    fig = artifact.fig
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
