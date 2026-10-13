"""Wire flowgx into the shared CLI. Loader + checks + renderer + Tool."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gxcore import Tool, run

from .checks import inspect_machine
from .machine import Machine, load_machine
from .render import render_image


@dataclass
class Scene:
    machine: Machine
    path: Path


def load(path: Path) -> Scene:
    machine, _ = load_machine(path)
    return Scene(machine=machine, path=Path(path))


def inspect(scene: Scene):
    return inspect_machine(scene.machine)


def render(scene: Scene, out: Path | None, dpi: float | None) -> Path:
    out = Path(out) if out else Path(f"{scene.path.stem}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    render_image(scene.machine).save(out)
    return out


def to_image(scene: Scene):
    return render_image(scene.machine)


TOOL = Tool(
    name="flowgx",
    description="Inspect state machines / flow charts for unreachable, stuck and non-deterministic states.",
    load=load,
    inspect=inspect,
    render=render,
    to_image=to_image,
    version="0.1.0",
)


def main(argv: list[str] | None = None) -> int:
    return run(TOOL, argv)
