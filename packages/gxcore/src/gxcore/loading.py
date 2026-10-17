"""Load an artifact from a Python file the agent wrote.

Every tool accepts the same shapes, so the discovery logic is written once:

  * a module-level attribute (``fig``, ``level``, ``machine``, …)
  * a builder callable (``build()``, ``make_…()``) returning one
  * a tool-specific fallback

State is kept out of the module cache's way by loading under a unique name.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from types import ModuleType
from typing import Any, TypeVar

DEFAULT_BUILDERS = (
    "build",
    "make",
    "create",
    "make_figure",
    "figure",
    "create_figure",
    "make_level",
    "level_from_rows",
)


T = TypeVar("T")


class InvalidArtifact(ValueError):
    """A recognised declaration contains invalid data; do not try another shape."""


def convert_items(values: object, convert: Callable[[Any], T | None], *, field: str) -> list[T]:
    """Convert every declared member or reject it with its field and index."""
    if not isinstance(values, (list, tuple)):
        raise InvalidArtifact(f"{field}: expected a list or tuple")
    result: list[T] = []
    for index, value in enumerate(values):
        try:
            item = convert(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise InvalidArtifact(f"{field}[{index}]: {exc}") from exc
        if item is None:
            raise InvalidArtifact(f"{field}[{index}]: invalid declaration {value!r}")
        result.append(item)
    return result


def _name(value: object) -> str:
    if not isinstance(value, str):
        raise InvalidArtifact(f"expected a name, not {value!r}")
    return value


def convert_names(values: object, *, field: str) -> list[str]:
    """Convert a declared name collection, or reject it with field and index.

    Names are read as names: coercing an arbitrary object to `str` would turn a
    malformed declaration into a name that silently matches nothing.
    """
    return convert_items(values, _name, field=field)


_MODULES: ContextVar[dict[Path, ModuleType] | None] = ContextVar("gx_modules", default=None)


@contextmanager
def loading_session() -> Iterator[None]:
    """Share imported artifacts within one inspection, never across invocations."""
    token = _MODULES.set({})
    try:
        yield
    finally:
        _MODULES.reset(token)


def load_module(path: str | Path) -> ModuleType:
    path = Path(path)
    modules = _MODULES.get()
    key = path.resolve()
    if modules is not None and key in modules:
        return modules[key]
    if not path.exists():
        raise FileNotFoundError(path)
    # A FIFO named `*.py` exists and reading it blocks forever (measured: a
    # directory run holding one FIFO never returned, so the tool produced no report
    # and no exit code at all). Only a regular file is read.
    if not path.is_file():
        raise InvalidArtifact(f"{path}: not a regular file, so there is nothing to read")
    name = f"gx_under_test_{abs(hash(str(path)))}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load a Python module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    # An artifact can end the process itself. `os._exit` is not an exception, so it
    # was not caught: measured, `os._exit(0)` returned exit 0 with no report at all
    # ("inspected, no error") and `os._exit(42)` returned 42, a code outside the
    # contract's table. The artifact runs in *this* process, so the exit is trapped
    # here and reported like any other refusal.
    original_exit = os._exit

    def _refuse(code: object = None) -> None:
        raise InvalidArtifact(f"the artifact called os._exit({code!r}) while loading")

    os._exit = _refuse  # type: ignore[assignment]
    try:
        # Inspect the current source, not a timestamp/size-matched cached .pyc.
        exec(compile(path.read_bytes(), str(path), "exec", dont_inherit=True), module.__dict__)
    finally:
        os._exit = original_exit
    if modules is not None:
        modules[key] = module
    return module


def resolve(
    module: ModuleType,
    attrs: Sequence[str] = (),
    builders: Sequence[str] = DEFAULT_BUILDERS,
    convert: Callable[[Any], Any] | None = None,
) -> Any:
    """First value that satisfies ``convert`` (or is not None) among attrs then builders."""

    def ok(value: Any) -> Any:
        if value is None:
            return None
        if convert is None:
            return value
        try:
            return convert(value)
        except InvalidArtifact:
            raise
        except Exception:
            return None

    for name in attrs:
        if hasattr(module, name):
            found = ok(getattr(module, name))
            if found is not None:
                return found

    for name in builders:
        fn = getattr(module, name, None)
        if callable(fn):
            found = ok(fn())
            if found is not None:
                return found
    return None


def load_from_file(
    path: str | Path,
    *,
    attrs: Iterable[str],
    builders: Iterable[str] = DEFAULT_BUILDERS,
    convert: Callable[[Any], Any] | None = None,
    description: str = "artifact",
) -> tuple[Any, ModuleType]:
    module = load_module(path)
    found = resolve(module, tuple(attrs), tuple(builders), convert)
    if found is None:
        raise ValueError(
            f"{path}: no {description} found — define one of "
            f"{tuple(attrs)} or a builder returning one"
        )
    return found, module
