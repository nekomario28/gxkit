"""Directed-graph analysis shared by the tools.

`levelgx` walks a grid; `flowgx` walks a state machine. Both need the same
questions answered: what is reachable, what can reach a goal, what is reachable
but *cannot* get back (a trap / soft-lock), which nodes are dead ends, and is
there a cycle. The nodes are any hashable value; the tool decides what an edge
means.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Hashable, Iterable, Iterator, Mapping

Adjacency = Mapping[Hashable, Iterable[Hashable]]


def _norm(edges: Adjacency) -> dict[Hashable, list[Hashable]]:
    return {u: list(vs) for u, vs in edges.items()}


def reachable(edges: Adjacency, starts: Iterable[Hashable]) -> set[Hashable]:
    """Everything reachable forward from ``starts``."""
    e = _norm(edges)
    seen = set(starts)
    q = deque(seen)
    while q:
        u = q.popleft()
        for v in e.get(u, ()):
            if v not in seen:
                seen.add(v)
                q.append(v)
    return seen


def reverse(edges: Adjacency) -> dict[Hashable, list[Hashable]]:
    r: dict[Hashable, list[Hashable]] = defaultdict(list)
    for u, vs in _norm(edges).items():
        for v in vs:
            r[v].append(u)
    return dict(r)


def can_reach(edges: Adjacency, targets: Iterable[Hashable]) -> set[Hashable]:
    """Everything from which some target is reachable (reverse BFS)."""
    r = reverse(edges)
    seen = set(targets)
    q = deque(seen)
    while q:
        v = q.popleft()
        for u in r.get(v, ()):
            if u not in seen:
                seen.add(u)
                q.append(u)
    return seen


def distances(edges: Adjacency, start: Hashable) -> dict[Hashable, int]:
    """Shortest-path distance from ``start`` to every reachable node."""
    e = _norm(edges)
    dist = {start: 0}
    q = deque([start])
    while q:
        u = q.popleft()
        for v in e.get(u, ()):
            if v not in dist:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist


def shortest_path(edges: Adjacency, start: Hashable, target: Hashable) -> list[Hashable] | None:
    """A shortest path ``start -> target`` as a list of nodes, or None."""
    if start == target:
        return [start]
    e = _norm(edges)
    parent: dict[Hashable, Hashable] = {start: start}
    q = deque([start])
    while q:
        u = q.popleft()
        for v in e.get(u, ()):
            if v not in parent:
                parent[v] = u
                if v == target:
                    path = [v]
                    while path[-1] != start:
                        path.append(parent[path[-1]])
                    return list(reversed(path))
                q.append(v)
    return None


def traps(
    edges: Adjacency,
    starts: Iterable[Hashable],
    targets: Iterable[Hashable],
) -> set[Hashable]:
    """Reachable nodes from which no target can be reached.

    This is the soft-lock set: the agent can get in, but the goal is gone. It is
    empty whenever the graph is symmetric (an undirected graph has no traps).
    """
    targets = set(targets)
    r = reachable(edges, starts)
    safe = can_reach(edges, targets)
    return r - safe - targets


def unreachable(edges: Adjacency, starts: Iterable[Hashable], nodes: Iterable[Hashable]) -> set[Hashable]:
    return set(nodes) - reachable(edges, starts)


def terminals(edges: Adjacency, nodes: Iterable[Hashable]) -> list[Hashable]:
    """Nodes with no outgoing edge."""
    e = _norm(edges)
    return [n for n in nodes if not e.get(n)]


def weak_components(edges: Adjacency) -> list[set[Hashable]]:
    """Connected components ignoring edge direction."""
    und: dict[Hashable, set[Hashable]] = defaultdict(set)
    for u, vs in _norm(edges).items():
        und[u]
        for v in vs:
            und[u].add(v)
            und[v].add(u)
    seen: set[Hashable] = set()
    out: list[set[Hashable]] = []
    for node in und:
        if node in seen:
            continue
        comp = {node}
        q = deque([node])
        seen.add(node)
        while q:
            u = q.popleft()
            for v in und[u]:
                if v not in seen:
                    seen.add(v)
                    comp.add(v)
                    q.append(v)
        out.append(comp)
    return out


def find_cycle(edges: Adjacency) -> list[Hashable] | None:
    """Any cycle, as a node list ending where it starts, or None.

    Iterative on purpose: a deep chain (thousands of modules) must not hit the
    recursion limit and crash the tool.
    """
    e = _norm(edges)
    WHITE, GREY, BLACK = 0, 1, 2
    color: dict[Hashable, int] = defaultdict(int)
    for start in list(e):
        if color[start] != WHITE:
            continue
        color[start] = GREY
        path: list[Hashable] = [start]
        stack: list[tuple[Hashable, Iterator[Hashable]]] = [(start, iter(e.get(start, ())))]
        while stack:
            node, it = stack[-1]
            advanced = False
            for v in it:
                if color[v] == GREY:
                    return path[path.index(v):] + [v]
                if color[v] == WHITE:
                    color[v] = GREY
                    path.append(v)
                    stack.append((v, iter(e.get(v, ()))))
                    advanced = True
                    break
            if not advanced:
                color[node] = BLACK
                stack.pop()
                path.pop()
    return None
