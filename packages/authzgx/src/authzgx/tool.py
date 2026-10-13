"""Wire authzgx into the shared CLI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gxcore import Tool, run

from .authmodel import AuthModel, load_model
from .checks import inspect_auth
from .render import render_image


@dataclass
class Scene:
    model: AuthModel
    path: Path


def load(path: Path) -> Scene:
    model, _ = load_model(path)
    return Scene(model=model, path=Path(path))


def inspect(scene: Scene):
    return inspect_auth(scene.model)


def render(scene: Scene, out: Path | None, dpi: float | None) -> Path:
    out = Path(out) if out else Path(f"{scene.path.stem}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    render_image(scene.model).save(out)
    return out


def to_image(scene: Scene):
    return render_image(scene.model)


TOOL = Tool(
    name="authzgx",
    description="Inspect permission models for privilege-escalation paths, cycles and dead config.",
    load=load,
    inspect=inspect,
    render=render,
    to_image=to_image,
    version="0.1.0",
    origin="top-left",
)


def main(argv: list[str] | None = None) -> int:
    return run(TOOL, argv)
