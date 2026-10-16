"""A network topology: nodes with a kind, and the traffic allowed between them.

    import netgx as n

    net = n.Network(
        nodes={"internet": "public", "web": "service", "db": "data"},
        edges=[("internet", "web"), ("web", "db")],
        sensitive=["db"],
    )

A node's kind is `public` (reachable from outside), `edge`, `service` or `data`.
The checks ask the least-privilege question: can a public node reach something
sensitive?
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

KINDS = ("public", "edge", "service", "data")


@dataclass
class Network:
    nodes: dict[str, str] = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)
    sensitive: list[str] = field(default_factory=list)
    name: str = "network"

    def names(self) -> list[str]:
        return list(self.nodes)

    def graph(self) -> dict[str, list[str]]:
        graph: dict[str, list[str]] = {name: [] for name in self.nodes}
        for src, dst in self.edges:
            graph.setdefault(src, []).append(dst)
            graph.setdefault(dst, [])
        return graph

    def public(self) -> list[str]:
        return [name for name, kind in self.nodes.items() if kind == "public"]

    def sensitive_nodes(self) -> tuple[list[str], bool]:
        """`(names, by_kind)`: what the exposure question is about, and why.

        A *declared* list is authoritative. When it names no node at all, that is a
        typo `dangling-reference` already reports, and standing in the `data` nodes
        would answer a question nobody asked — measured: `sensitive=["ghost"]`
        reported an exposure of a node the artifact never called sensitive. An
        *empty* list is different: nothing was declared, `data` nodes stand in, and
        `by_kind` is what lets the finding say so instead of asserting a fact the
        model never stated.
        """
        explicit = [name for name in self.sensitive if name in self.nodes]
        if self.sensitive:
            return explicit, False
        return [name for name, kind in self.nodes.items() if kind == "data"], True


def _as_network(value: object) -> Network | None:
    if isinstance(value, Network):
        return value
    if isinstance(value, dict) and ("nodes" in value or "edges" in value):
        return Network(
            nodes={str(k): str(v) for k, v in dict(value.get("nodes", {})).items()},
            edges=[(str(a), str(b)) for a, b in value.get("edges", [])],
            sensitive=[str(s) for s in value.get("sensitive", [])],
            name=str(value.get("name", "network")),
        )
    return None


def load_network(path: str | Path) -> tuple[Network, object]:
    from gxcore.loading import load_module, resolve

    path = Path(path)
    module = load_module(path)
    net = resolve(
        module,
        attrs=("network", "NETWORK", "net", "topology"),
        builders=("build", "make_network", "make"),
        convert=_as_network,
    )
    if net is None:
        nodes = getattr(module, "NODES", None)
        if nodes is not None:
            net = Network(
                nodes={str(k): str(v) for k, v in dict(nodes).items()},
                edges=[(str(a), str(b)) for a, b in getattr(module, "EDGES", [])],
                sensitive=[str(s) for s in getattr(module, "SENSITIVE", [])],
            )
    if net is None:
        raise ValueError(f"{path}: no network found — define `network` (a Network) or NODES/EDGES")
    net.name = getattr(module, "NAME", path.stem)
    return net, module


def network_from_parts(
    nodes: dict[str, str] | None = None,
    edges: list[tuple[str, str]] | None = None,
    sensitive: list[str] | None = None,
    name: str = "network",
) -> Network:
    return Network(
        nodes=dict(nodes or {}),
        edges=[(a, b) for a, b in (edges or [])],
        sensitive=list(sensitive or []),
        name=name,
    )
