"""Load a chart from a Python file the agent wrote.

Accept a module-level ``fig``, a builder returning a Figure, or whatever
``matplotlib.pyplot`` has open. The Agg backend is forced before the module is
imported so headless runs match desktops.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)

_BUILDERS = ("fig", "figure", "build", "make_figure", "create_figure", "make", "create")


def _as_figure(value: Any) -> Any:
    from matplotlib.figure import Figure

    return value if isinstance(value, Figure) else None


def load_figure(path: str | Path) -> tuple[Any, Any]:
    """Return ``(figure, module)`` for a chart file."""
    import matplotlib.pyplot as plt
    from gxcore.loading import load_from_file

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    plt.close("all")
    try:
        return load_from_file(
            path,
            attrs=("fig", "figure"),
            builders=_BUILDERS,
            convert=_as_figure,
            description="figure (a matplotlib Figure)",
        )
    except ValueError:
        numbers = plt.get_fignums()
        if numbers:
            return plt.figure(numbers[-1]), None
        raise
