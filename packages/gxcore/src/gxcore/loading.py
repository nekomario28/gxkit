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


def validate_names(value: object, *, field: str) -> None:
    """Names, or a located refusal.

    For a model's `__post_init__`, which returns nothing: a model *built in Python* with a
    wrong-typed field reached the inspector and raised a bare `TypeError`/`AttributeError`
    there (measured: `Run("a", start="oops")`, `Endpoint(200, "/x")`, `Machine(states=[7])`
    and ten more), so the refusal belongs where the field is set.
    """
    convert_names(value, field=field)


def validate_pairs(value: object, *, field: str, arity: int | tuple[int, ...]) -> None:
    """Pairs (or tuples of one of ``arity`` lengths), or a located refusal."""
    lengths = arity if isinstance(arity, tuple) else (arity,)
    for index, item in enumerate(convert_items(value, lambda item: item, field=field)):
        if not isinstance(item, (list, tuple)) or len(item) not in lengths:
            expected = " or ".join(str(length) for length in lengths)
            raise InvalidArtifact(f"{field}[{index}]: expected {expected} names, not {item!r}")
        for part in item:
            _name(part)


def validate_mapping(value: object, *, field: str) -> None:
    convert_mapping(value, field=field)


def validate_number(value: object, *, field: str, integer: bool = False) -> None:
    convert_number(value, field=field, integer=integer)


def validate_optional_number(value: object, *, field: str, integer: bool = False) -> None:
    if value is not None:
        convert_number(value, field=field, integer=integer)


def validate_flag(value: object, *, field: str) -> None:
    convert_bool(value, field=field)


def convert_bool(value: object, *, field: str) -> bool:
    """A declared flag, or a located refusal.

    `bool("no")` is `True`, so a string where a flag belongs made the tool assert the
    opposite of the declaration: measured, `secret = "no"` produced a
    `secret-with-default` *error*, `DETERMINISTIC = "no"` reported `deterministic`, and
    `EXPECT_AUDIO = "no"` expected an audio track. The OpenAPI importer has guarded this
    for `deprecated` since its own review; the declaration route did not.
    """
    if not isinstance(value, bool):
        raise InvalidArtifact(f"{field}: expected true or false, not {value!r}")
    return value


def convert_number(value: object, *, field: str, integer: bool = False) -> float:
    """A declared number, or a located refusal. `bool` is not a number here."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidArtifact(f"{field}: expected a number, not {value!r}")
    if integer and float(value) != int(value):
        raise InvalidArtifact(f"{field}: expected a whole number, not {value!r}")
    return float(value)


def convert_pairs(
    values: object, *, field: str, arity: int, names: bool = True
) -> list[tuple[Any, ...]]:
    """Declared pairs/triples, or a located refusal.

    A string is not a list of names (it is eight characters), and a tuple with a
    fourth element in a three-element list was silently truncated: measured,
    `TRANSITIONS = [("a", "b", "e", "extra")]` dropped `extra` and `STATES = "ab"`
    became the states `a` and `b` — a clean, finishable machine invented from a
    declaration that contained none.
    """
    items = convert_items(values, lambda value: value, field=field)
    out: list[tuple[Any, ...]] = []
    for index, item in enumerate(items):
        if not isinstance(item, (list, tuple)) or len(item) != arity:
            raise InvalidArtifact(f"{field}[{index}]: expected {arity} names, not {item!r}")
        parts = tuple(_name(part) if names else part for part in item)
        out.append(parts)
    return out


def convert_mapping(value: object, *, field: str) -> dict[str, Any]:
    """A declared name→value mapping, or a located refusal.

    `dict("AB")` and `dict([("a",)])` fail with messages about sequence elements —
    naming neither the declaration nor the field — and a string that happens to look
    like pairs was read as one.
    """
    if not isinstance(value, dict):
        raise InvalidArtifact(f"{field}: expected a mapping, not {value!r}")
    return {_name(key): item for key, item in value.items()}


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
