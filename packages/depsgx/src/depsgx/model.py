"""A module dependency graph, declared as data.

    import depsgx as d

    graph = d.ModuleGraph(
        modules=["api", "service", "domain", "util"],
        depends=[("api", "service"), ("service", "domain"), ("domain", "util")],
        roots=["api"],                          # entry points
        layers=[["api"], ["service"], ["domain"], ["util"]],  # top -> bottom
        forbidden=[("domain", "infra")],        # explicit layering bans
    )

``depends`` edges point from a module to what it imports. `roots` are the entry
points (apps, binaries); anything not reachable from them is dead code. With
`layers`, a dependency that points *upward* (a lower layer importing a higher
one) is a layer violation.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from gxcore.graph import reachable


@dataclass
class ModuleGraph:
    modules: list[str] = field(default_factory=list)
    depends: list[tuple[str, str]] = field(default_factory=list)
    roots: list[str] = field(default_factory=list)
    forbidden: list[tuple[str, str]] = field(default_factory=list)
    layers: list[list[str]] = field(default_factory=list)
    name: str = "modules"

    def edges(self) -> dict[str, list[str]]:
        e: dict[str, list[str]] = {m: [] for m in self.modules}
        for src, dst in self.depends:
            e.setdefault(src, []).append(dst)
            e.setdefault(dst, [])
        return e

    def layer_of(self, module: str) -> int | None:
        for index, group in enumerate(self.layers):
            if module in group:
                return index
        return None

    def reachable_from_roots(self) -> set[str]:
        if not self.roots:
            return set(self.modules)
        return reachable(self.edges(), self.roots)


def _as_graph(value: object) -> ModuleGraph | None:
    return value if isinstance(value, ModuleGraph) else None


def load_graph(path: str | Path) -> tuple[ModuleGraph, object]:
    from gxcore.loading import load_module, resolve

    path = Path(path)
    module = load_module(path)
    graph = resolve(
        module,
        attrs=("graph", "MODULES", "deps", "DEPENDS", "module_graph"),
        builders=("build", "make_graph", "make"),
        convert=_as_graph,
    )
    if graph is None:
        depends = getattr(module, "DEPENDS", getattr(module, "depends", None))
        if depends is not None:
            graph = ModuleGraph(
                modules=list(getattr(module, "MODULES", getattr(module, "modules", []))),
                depends=[(d[0], d[1]) for d in depends],
                roots=list(getattr(module, "ROOTS", getattr(module, "roots", []))),
                forbidden=[
                    (f[0], f[1])
                    for f in getattr(module, "FORBIDDEN", getattr(module, "forbidden", []))
                ],
                layers=[list(g) for g in getattr(module, "LAYERS", getattr(module, "layers", []))],
            )
    if graph is None:
        raise ValueError(
            f"{path}: no module graph found — define `graph` (a ModuleGraph) or "
            "MODULES/DEPENDS/ROOTS lists"
        )
    if graph.name == "modules":
        graph.name = getattr(module, "NAME", path.stem)
    return graph, module


def modules_from_parts(
    modules: Iterable[str] | None = None,
    depends: Iterable[tuple[str, str]] | None = None,
    roots: Iterable[str] | None = None,
    forbidden: Iterable[tuple[str, str]] | None = None,
    layers: Iterable[Iterable[str]] | None = None,
    name: str = "modules",
) -> ModuleGraph:
    return ModuleGraph(
        modules=list(modules or []),
        depends=[(d[0], d[1]) for d in (depends or [])],
        roots=list(roots or []),
        forbidden=[(f[0], f[1]) for f in (forbidden or [])],
        layers=[list(g) for g in (layers or [])],
        name=name,
    )
