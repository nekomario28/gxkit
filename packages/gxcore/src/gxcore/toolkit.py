"""Build a raster tool from three callables.

`flowgx`, `authzgx`, `depsgx` (and `levelgx`) differ only in how they load an
artifact, inspect it, and draw it. Everything between — wrapping the artifact
with its path, saving the PNG, wiring the `Tool` and `main` — is the same, so it
lives here.

    main, TOOL = scene_tool(
        name="depsgx",
        description="…",
        load=load_graph,        # Path -> (artifact, module)
        inspect=inspect_graph,  # artifact -> Report
        to_image=render_image,  # artifact -> PIL.Image
    )
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cli import Tool, run


def distribution_version(name: str, fallback: str = "0.0.0") -> str:
    """The installed version of a distribution, so `--version` cannot drift
    from `pyproject.toml`."""
    try:
        from importlib.metadata import version

        return version(name)
    except Exception:
        return fallback


@dataclass
class Scene:
    artifact: Any
    path: Path


def scene_tool(
    *,
    name: str,
    description: str,
    load: Callable[[Path], tuple[Any, Any]],
    inspect: Callable[[Any], Any],
    to_image: Callable[[Any], Any],
    version: str | None = None,
    origin: str = "top-left",
) -> tuple[Callable[[list[str] | None], int], Tool]:
    def _load(path: Path) -> Scene:
        artifact, _module = load(path)
        return Scene(artifact, Path(path))

    def _inspect(scene: Scene):
        return inspect(scene.artifact)

    def _render(scene: Scene, out: Path | None, dpi: float | None) -> Path:
        out = Path(out) if out else Path(f"{scene.path.stem}.png")
        out.parent.mkdir(parents=True, exist_ok=True)
        image = to_image(scene.artifact)
        if dpi:
            image.save(out, dpi=(dpi, dpi))
        else:
            image.save(out)
        return out

    def _to_image(scene: Scene):
        return to_image(scene.artifact)

    tool = Tool(
        name=name,
        description=description,
        load=_load,
        inspect=_inspect,
        render=_render,
        to_image=_to_image,
        version=version or distribution_version(name),
        origin=origin,
    )

    def main(argv: list[str] | None = None) -> int:
        return run(tool, argv)

    return main, tool
