"""Wire levelgx into the shared CLI. Loader + checks + renderer + Tool."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gxcore import Tool, run

from .checks import inspect_level
from .level import Level, load_level
from .render import render_image


@dataclass
class Scene:
    level: Level
    path: Path


def load(path: Path) -> Scene:
    level, _ = load_level(path)
    return Scene(level=level, path=Path(path))


def inspect(scene: Scene):
    return inspect_level(scene.level)


def render(scene: Scene, out: Path | None, dpi: float | None) -> Path:
    out = Path(out) if out else Path(f"{scene.path.stem}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    render_image(scene.level).save(out)
    return out


def to_image(scene: Scene):
    return render_image(scene.level)


TOOL = Tool(
    name="levelgx",
    description="Inspect game levels for reachability, solvability and soft-locks.",
    load=load,
    inspect=inspect,
    render=render,
    to_image=to_image,
    version="0.1.0",
    origin="top-left",
)


def main(argv: list[str] | None = None) -> int:
    return run(TOOL, argv)
