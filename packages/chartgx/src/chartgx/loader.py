"""Load a chart from a Python file the agent wrote.

Accept, in order: a module-level ``fig``, a builder callable returning a Figure,
or whatever ``matplotlib.pyplot`` has open. The Agg backend is forced before the
module is imported so headless runs match desktops.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)

_BUILDERS = ("build", "make_figure", "figure", "create_figure")


def _module_from_path(path: Path) -> ModuleType:
    name = f"chartgx_under_test_{abs(hash(str(path)))}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load a Python module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_figure(path: str | Path) -> tuple[Any, ModuleType]:
    """Return ``(figure, module)`` for a chart file."""
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    plt.close("all")
    module = _module_from_path(path)

    fig = getattr(module, "fig", None)
    if isinstance(fig, Figure):
        return fig, module

    for name in _BUILDERS:
        fn = getattr(module, name, None)
        if callable(fn):
            fig = fn()
            if isinstance(fig, Figure):
                return fig, module

    nums = plt.get_fignums()
    if nums:
        return plt.figure(nums[-1]), module

    raise ValueError(
        f"{path}: no figure found — define `fig`, a `build()` returning one, "
        "or open one with matplotlib.pyplot"
    )
