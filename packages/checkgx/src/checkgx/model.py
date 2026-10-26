"""A check registry, declared as data.

    import checkgx as c

    registry = c.Registry(
        checks=["a_probe_passes", "b_strings_match", "b_strings_match"],
        evaluated=["a_probe_passes", "b_strings_match"],
        metadata=["status", "note"],
    )

`checks` is what the author wrote, in order, duplicates included - a dict literal
that repeats a key keeps only one, so the repetition itself is the finding.
`evaluated` is what the runner actually reads: the union of every mapping whose
values it treats as checks. `metadata` is what sits beside them in the report and
is never evaluated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from gxcore.loading import validate_names


@dataclass
class Registry:
    checks: list[str] = field(default_factory=list)
    evaluated: list[str] = field(default_factory=list)
    metadata: list[str] = field(default_factory=list)
    name: str = "checks"

    def declared(self) -> dict[str, int]:
        """Name -> how many times it was written."""
        counts: dict[str, int] = {}
        for name in self.checks:
            counts[name] = counts.get(name, 0) + 1
        return counts


def _as_registry(value: object) -> Registry | None:
    return value if isinstance(value, Registry) else None


def load_registry(path: str | Path) -> tuple[Registry, object]:
    """Load a model file and return the registry it declares."""
    from gxcore.loading import load_module, resolve

    module = load_module(Path(path))
    registry = resolve(
        module,
        attrs=("registry", "REGISTRY", "checks", "CHECKS"),
        builders=("build", "make_registry", "make"),
        convert=_as_registry,
    )
    if registry is None:
        raise ValueError(f"{path}: no check registry found — define CHECKS or a builder returning one")
    return registry, module
