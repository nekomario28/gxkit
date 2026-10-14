"""Cross-check `gxcore.graph` against NetworkX on random directed graphs.

A hand-rolled reachability / cycle / shortest-path routine is exactly where a
quiet off-by-one hides. NetworkX is the reference; 300 random graphs per
property makes drift a failing test.
"""

from __future__ import annotations

import random

import networkx as nx
from gxcore.graph import (
    can_reach,
    distances,
    find_cycle,
    reachable,
    shortest_path,
    topological_sort,
    traps,
    weak_components,
)


def _random_edges(rng: random.Random) -> dict[int, list[int]]:
    n = rng.randint(1, 7)
    nodes = list(range(n))
    edges: dict[int, list[int]] = {u: [] for u in nodes}
    for u in nodes:
        for v in nodes:
            if rng.random() < 0.3:
                edges[u].append(v)
    return edges


def _digraph(edges: dict[int, list[int]]) -> nx.DiGraph:
    g = nx.DiGraph()
    g.add_nodes_from(edges)
    for u, vs in edges.items():
        for v in vs:
            g.add_edge(u, v)
    return g


def test_reachable_matches_networkx():
    rng = random.Random(11)
    for _ in range(300):
        edges = _random_edges(rng)
        g = _digraph(edges)
        start = rng.choice(list(edges))
        assert reachable(edges, [start]) == nx.descendants(g, start) | {start}


def test_can_reach_matches_networkx():
    rng = random.Random(12)
    for _ in range(300):
        edges = _random_edges(rng)
        g = _digraph(edges)
        targets = set(rng.sample(list(edges), rng.randint(1, len(edges))))
        want = {n for n in g if any(nx.has_path(g, n, t) for t in targets)}
        assert can_reach(edges, targets) == want


def test_distances_match_networkx():
    rng = random.Random(13)
    for _ in range(300):
        edges = _random_edges(rng)
        g = _digraph(edges)
        start = rng.choice(list(edges))
        assert distances(edges, start) == nx.single_source_shortest_path_length(g, start)


def test_shortest_path_matches_networkx():
    rng = random.Random(14)
    for _ in range(300):
        edges = _random_edges(rng)
        g = _digraph(edges)
        start, target = rng.choice(list(edges)), rng.choice(list(edges))
        path = shortest_path(edges, start, target)
        if nx.has_path(g, start, target):
            assert path is not None
            assert len(path) - 1 == nx.shortest_path_length(g, start, target)
        else:
            assert path is None


def test_find_cycle_matches_networkx():
    rng = random.Random(15)
    for _ in range(300):
        edges = _random_edges(rng)
        g = _digraph(edges)
        assert (find_cycle(edges) is not None) == (not nx.is_directed_acyclic_graph(g))


def test_weak_components_match_networkx():
    rng = random.Random(16)
    for _ in range(300):
        edges = _random_edges(rng)
        g = _digraph(edges)
        ours = {frozenset(c) for c in weak_components(edges)}
        theirs = {frozenset(c) for c in nx.weakly_connected_components(g)}
        assert ours == theirs


def test_traps_match_networkx():
    rng = random.Random(17)
    for _ in range(300):
        edges = _random_edges(rng)
        g = _digraph(edges)
        starts = [rng.choice(list(edges))]
        targets = set(rng.sample(list(edges), rng.randint(1, len(edges))))
        reached = reachable(edges, starts)
        want = {n for n in reached - targets if not any(nx.has_path(g, n, t) for t in targets)}
        assert traps(edges, starts, targets) == want


def test_topological_sort_matches_networkx():
    rng = random.Random(101)
    for _ in range(300):
        edges = _random_edges(rng)
        g = _digraph(edges)
        got = topological_sort(edges)
        if nx.is_directed_acyclic_graph(g):
            assert got is not None
            assert set(got) == set(edges)
            position = {node: i for i, node in enumerate(got)}
            for u, v in g.edges():
                assert position[u] < position[v], f"{u} must come before {v}"
        else:
            assert got is None


def test_topological_sort_includes_nodes_you_pass_in():
    edges = {1: [2], 3: []}
    order = topological_sort(edges, nodes=[3, 4])
    assert set(order) == {1, 2, 3, 4}
    position = {node: i for i, node in enumerate(order)}
    assert position[1] < position[2]
    assert topological_sort({1: [1]}) is None
