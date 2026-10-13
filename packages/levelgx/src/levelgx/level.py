"""A level is a grid of characters.

The legend is deliberately small and text-friendly, because an agent reads and
writes it:

    #  wall          .  floor         (space) also floor
    S  spawn         G  goal
    X  item          !  hazard (deadly: not walkable)
    >  one-way east  <  one-way west
    v  one-way south ^  one-way north

One-way tiles are what make a level *directed*: entering a ``>`` is only
possible from the west, and leaving it is only possible eastward. That is where
soft-locks come from, and why plain reachability is not enough.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

WALL = "#"
FLOOR = "."
SPACE = " "
SPAWN = "S"
GOAL = "G"
ITEM = "X"
HAZARD = "!"
ONEWAY: dict[str, tuple[int, int]] = {">": (0, 1), "<": (0, -1), "v": (1, 0), "^": (-1, 0)}
DIRS = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}


@dataclass
class Level:
    rows: list[str]
    name: str = "level"

    @property
    def width(self) -> int:
        return max((len(r) for r in self.rows), default=0)

    @property
    def height(self) -> int:
        return len(self.rows)

    def at(self, r: int, c: int) -> str | None:
        if 0 <= r < self.height and 0 <= c < len(self.rows[r]):
            return self.rows[r][c]
        return None

    def find(self, *chars: str) -> list[tuple[int, int]]:
        wanted = set(chars)
        return [(r, c) for r in range(self.height) for c in range(self.width)
                if self.at(r, c) in wanted]

    def spawn(self) -> tuple[int, int] | None:
        cells = self.find(SPAWN)
        return cells[0] if cells else None

    def goal(self) -> tuple[int, int] | None:
        cells = self.find(GOAL)
        return cells[0] if cells else None

    def items(self) -> list[tuple[int, int]]:
        return self.find(ITEM)

    def hazards(self) -> list[tuple[int, int]]:
        return self.find(HAZARD)

    def is_wall(self, r: int, c: int) -> bool:
        return self.at(r, c) in (WALL, None)

    def is_hazard(self, r: int, c: int) -> bool:
        return self.at(r, c) == HAZARD

    def is_floor(self, r: int, c: int) -> bool:
        """A cell an actor could stand on, ignoring hazards."""
        ch = self.at(r, c)
        return ch is not None and ch != WALL

    def passable(self, r: int, c: int, *, hazards_block: bool = True) -> bool:
        if self.is_wall(r, c):
            return False
        if hazards_block and self.is_hazard(r, c):
            return False
        return True

    def neighbors(self, r: int, c: int, *, hazards_block: bool = True) -> list[tuple[int, int]]:
        """Cells reachable from ``(r, c)`` in one step, honouring one-way tiles."""
        out: list[tuple[int, int]] = []
        here = self.at(r, c)
        for dr, dc in DIRS.values():
            nr, nc = r + dr, c + dc
            if not self.passable(nr, nc, hazards_block=hazards_block):
                continue
            step = (dr, dc)
            if here in ONEWAY and ONEWAY[here] != step:
                continue          # cannot leave against the arrow
            there = self.at(nr, nc)
            if there in ONEWAY and ONEWAY[there] != step:
                continue          # cannot enter against the arrow
            out.append((nr, nc))
        return out


def _module_from_path(path: Path) -> ModuleType:
    name = f"levelgx_under_test_{abs(hash(str(path)))}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load a Python module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _as_rows(value) -> list[str] | None:
    if isinstance(value, (list, tuple)) and value and all(isinstance(r, str) for r in value):
        return [r.replace("\t", "  ") for r in value]
    return None


def load_level(path: str | Path) -> tuple[Level, ModuleType]:
    """Return ``(level, module)`` for a level file.

    Accepts, in order: a module-level ``level`` (a `Level`), ``LEVEL``/``rows``
    (a list of strings), or a ``build()`` returning any of those.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    module = _module_from_path(path)

    value = getattr(module, "level", None)
    if isinstance(value, Level):
        value.name = getattr(module, "NAME", path.stem)
        return value, module

    for attr in ("LEVEL", "rows", "MAP", "map"):
        rows = _as_rows(getattr(module, attr, None))
        if rows is not None:
            return Level(rows, name=getattr(module, "NAME", path.stem)), module

    for builder in ("build", "make_level", "level_from_rows"):
        fn = getattr(module, builder, None)
        if callable(fn):
            value = fn()
            if isinstance(value, Level):
                value.name = getattr(module, "NAME", path.stem)
                return value, module
            rows = _as_rows(value)
            if rows is not None:
                return Level(rows, name=getattr(module, "NAME", path.stem)), module

    raise ValueError(
        f"{path}: no level found — define `level` (a Level), `LEVEL`/`rows` "
        "(a list of strings), or a `build()` returning one"
    )
