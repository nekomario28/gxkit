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


def route_to(edges: Adjacency[_H], targets: Iterable[_H]) -> dict[_H, _H]:
    """For every node that can reach a target, the next hop on a shortest route.

    ``route_to(g, [t])[u]`` is where to step from ``u`` so that ``t`` is reached in
    the fewest hops; a target maps to itself. One reverse traversal from all the
    targets answers it for *every* starting node at once, where `shortest_path`
    answers it for one start — so a caller that needs a route from many starts (or
    only the path's length) asks once instead of once per start.

    A node absent from the result cannot reach any target. Walking the map from a
    node that is in it lands on a target in ``len(walk) - 1`` hops (`route_nodes`
    does that walk). Deterministic: ties break in ``targets`` order, and then in
    adjacency order.
    """
    ordered = list(dict.fromkeys(targets))
    hop: dict[_H, _H] = {t: t for t in ordered}
    q = deque(ordered)
    r = reverse(edges)
    while q:
        v = q.popleft()
        for u in r.get(v, ()):
            if u not in hop:
                hop[u] = v
                q.append(u)
    return hop


def route_nodes(hop: Mapping[_H, _H], start: _H) -> list[_H] | None:
    """The node list a `route_to` map describes from ``start``, or None.

    The walk is separate from the map so the map can be built once for many starts
    and walked cheaply per finding; this is the one place a route is turned into the
    node list a message shows.
    """
    if start not in hop:
        return None
    path = [start]
    while hop[path[-1]] != path[-1]:
        path.append(hop[path[-1]])
    return path


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


def cycle_witnesses(
    edges: Adjacency[_H], *, self_loops: bool = True
) -> list[tuple[list[_H], list[_H]]]:
    """One cycle witness per cyclic component, with the component it belongs to.

    A single global `find_cycle` reports the first cycle it meets and hides the
    rest, so a graph with two independent cycles looks like a graph with one. A
    caller that reports cycles — a dependency graph, a role hierarchy, a build
    DAG, a foreign-key graph — must report every component, and it must identify
    the finding by the component rather than by whichever node the search
    happened to start from, or a rotated witness reads as new debt.

    `self_loops` decides whether an edge from a node to itself is a cycle, and the
    answer is the *domain's*, not the graph's: a role that inherits itself is an
    escalation loop (`authzgx` reports it), while a table whose foreign key points
    at itself is how a self-referencing tree is written (`schemagx` does not), a
    module that imports itself has its own `self-dependency` finding (`depsgx`), and
    a state or protocol step that returns to itself is a retry whose real fault — no
    way out — is reported as `dead-end`/`no-exit` (`flowgx`, `protogx`).

    Returns ``(witness, sorted_component)`` pairs in a deterministic order, and an
    empty list when the graph is acyclic.
    """
    e = _norm(edges)
    witnesses: list[tuple[list[_H], list[_H]]] = []
    for component in strongly_connected_components(e):
        if len(component) < 2:
            # A size-one component is cyclic exactly when the node reaches itself, and
            # whether that is a fault depends on the domain (`self_loops` above).
            # `len(component) < 2: continue` reported a self-inheriting role as clean
            # (measured: `authzgx` with `editor -> editor` exit 0, while the same cycle
            # spread over two roles was an error).
            only = component[0] if component else None
            if not self_loops or only is None or only not in e.get(only, ()):
                continue
            witnesses.append(([only, only], [only]))
            continue
        members = set(component)
        inside: dict[_H, list[_H]] = {
            node: [dst for dst in e.get(node, ()) if dst in members] for node in component
        }
        witness = find_cycle(inside)
        if witness:
            # Sorted by name: nodes are names in every caller, and this is
            # deterministic for any hashable so the fingerprint cannot move.
            witnesses.append((witness, sorted(component, key=str)))
    return witnesses


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
