"""Load an artifact from a Python file the agent wrote.

Every tool accepts the same shapes, so the discovery logic is written once:

  * a module-level attribute (``fig``, ``level``, ``machine``, …)
  * a builder callable (``build()``, ``make_…()``) returning one
  * a tool-specific fallback

State is kept out of the module cache's way by loading under a unique name.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Iterable, Sequence

DEFAULT_BUILDERS = ("build", "make", "create", "make_figure", "figure", "create_figure",
                    "make_level", "level_from_rows")


def load_module(path: str | Path) -> ModuleType:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    name = f"gx_under_test_{abs(hash(str(path)))}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load a Python module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
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
