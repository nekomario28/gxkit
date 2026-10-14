"""Directed-graph analysis shared by the tools.

`levelgx` walks a grid; `flowgx` walks a state machine. Both need the same
questions answered: what is reachable, what can reach a goal, what is reachable
but *cannot* get back (a trap / soft-lock), which nodes are dead ends, and is
there a cycle. The nodes are any hashable value; the tool decides what an edge
means.
"""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Hashable, Iterable, Iterator, Mapping
from typing import TypeVar

_H = TypeVar("_H", bound=Hashable)
Adjacency = Mapping[_H, Iterable[_H]]


def _norm(edges: Adjacency[_H]) -> dict[_H, list[_H]]:
    return {u: list(vs) for u, vs in edges.items()}


def reachable(edges: Adjacency[_H], starts: Iterable[_H]) -> set[_H]:
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


def reverse(edges: Adjacency[_H]) -> dict[_H, list[_H]]:
    r: dict[_H, list[_H]] = defaultdict(list)
    for u, vs in _norm(edges).items():
        for v in vs:
            r[v].append(u)
    return dict(r)


def can_reach(edges: Adjacency[_H], targets: Iterable[_H]) -> set[_H]:
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


def distances(edges: Adjacency[_H], start: _H) -> dict[_H, int]:
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


def shortest_path(edges: Adjacency[_H], start: _H, target: _H) -> list[_H] | None:
    """A shortest path ``start -> target`` as a list of nodes, or None."""
    if start == target:
        return [start]
    e = _norm(edges)
    parent: dict[_H, _H] = {start: start}
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
    edges: Adjacency[_H],
    starts: Iterable[_H],
    targets: Iterable[_H],
) -> set[_H]:
    """Reachable nodes from which no target can be reached.

    This is the soft-lock set: the agent can get in, but the goal is gone. It is
    empty whenever the graph is symmetric (an undirected graph has no traps).
    """
    targets = set(targets)
    r = reachable(edges, starts)
    safe = can_reach(edges, targets)
    return r - safe - targets


def unreachable(edges: Adjacency[_H], starts: Iterable[_H], nodes: Iterable[_H]) -> set[_H]:
    reached = reachable(edges, starts)
    return set(nodes) - reached


def terminals(edges: Adjacency[_H], nodes: Iterable[_H]) -> list[_H]:
    """Nodes with no outgoing edge."""
    e = _norm(edges)
    return [n for n in nodes if not e.get(n)]


def weak_components(edges: Adjacency[_H]) -> list[set[_H]]:
    """Connected components ignoring edge direction."""
    und: dict[_H, set[_H]] = defaultdict(set)
    for u, vs in _norm(edges).items():
        und[u]
        for v in vs:
            und[u].add(v)
            und[v].add(u)
    seen: set[_H] = set()
    out: list[set[_H]] = []
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


def find_cycle(edges: Adjacency[_H]) -> list[_H] | None:
    """Any cycle, as a node list ending where it starts, or None.

    Iterative on purpose: a deep chain (thousands of modules) must not hit the
    recursion limit and crash the tool.
    """
    e = _norm(edges)
    WHITE, GREY, BLACK = 0, 1, 2
    color: dict[_H, int] = defaultdict(int)
    for start in list(e):
        if color[start] != WHITE:
            continue
        color[start] = GREY
        path: list[_H] = [start]
        stack: list[tuple[_H, Iterator[_H]]] = [(start, iter(e.get(start, ())))]
        while stack:
            node, it = stack[-1]
            advanced = False
            for v in it:
                if color[v] == GREY:
                    return [*path[path.index(v) :], v]
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


def topological_sort(edges: Adjacency[_H], nodes: Iterable[_H] | None = None) -> list[_H] | None:
    """An order where every node comes before the nodes it points to, or
    ``None`` if the graph has a cycle.

    Deterministic: ties break in the order nodes first appear in ``edges`` (and
    then ``nodes``). Kahn's algorithm, iterative like the rest of this module.
    """
    e = _norm(edges)
    ordered: list[_H] = []
    seen: set[_H] = set()

    def remember(n: _H) -> None:
        if n not in seen:
            seen.add(n)
            ordered.append(n)

    if nodes is not None:
        for n in nodes:
            remember(n)
    for u, vs in e.items():
        remember(u)
        for v in vs:
            remember(v)

    indegree: dict[_H, int] = dict.fromkeys(ordered, 0)
    for vs in e.values():
        for v in vs:
            indegree[v] += 1

    queue = deque(n for n in ordered if indegree[n] == 0)
    out: list[_H] = []
    while queue:
        u = queue.popleft()
        out.append(u)
        for v in e.get(u, ()):
            indegree[v] -= 1
            if indegree[v] == 0:
                queue.append(v)
    return out if len(out) == len(ordered) else None


def strongly_connected_components(edges: Adjacency[_H]) -> list[list[_H]]:
    """The graph's strongly connected components, each a list of nodes.

    Every node appears in exactly one component; a node with no cycle is its own.
    Kosaraju's algorithm, iterative (a deep chain must not hit the recursion
    limit). Deterministic for a given input.
    """
    e = _norm(edges)
    nodes: list[_H] = []
    seen: set[_H] = set()
    for u, vs in e.items():
        if u not in seen:
            seen.add(u)
            nodes.append(u)
        for v in vs:
            if v not in seen:
                seen.add(v)
                nodes.append(v)

    # first pass: the DFS finishing order
    visited: set[_H] = set()
    finish: list[_H] = []
    for start in nodes:
        if start in visited:
            continue
        visited.add(start)
        stack: list[tuple[_H, Iterator[_H]]] = [(start, iter(e.get(start, ())))]
        while stack:
            node, it = stack[-1]
            advanced = False
            for w in it:
                if w not in visited:
                    visited.add(w)
                    stack.append((w, iter(e.get(w, ()))))
                    advanced = True
                    break
            if not advanced:
                finish.append(node)
                stack.pop()

    # second pass: on the reversed graph, in reverse finishing order
    rev = reverse(e)
    assigned: set[_H] = set()
    components: list[list[_H]] = []
    for start in reversed(finish):
        if start in assigned:
            continue
        component: list[_H] = []
        queue = [start]
        assigned.add(start)
        while queue:
            u = queue.pop()
            component.append(u)
            for w in rev.get(u, ()):
                if w not in assigned:
                    assigned.add(w)
                    queue.append(w)
        components.append(component)
    return components
