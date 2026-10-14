"""Invariants of the circular diagram layout.

`render` is what every node-link tool hands the storyboard, so the coordinates
must be stable and sane: the same graph draws the same pixels, nodes do not sit
on top of each other, and nothing spills off the canvas. These are properties,
checked on random graphs — not a golden image that would hide a layout drift.
"""

from __future__ import annotations

import math
import random
from itertools import pairwise

import pytest
from gxcore.diagram import BACKGROUND, Edge, Node, image_size, layout, node_box, render
from PIL import Image

SEEDS = range(40)


def _ids(n: int) -> list[str]:
    return [f"n{i}" for i in range(n)]


def _graph(rng: random.Random, n: int) -> tuple[list[Node], list[Edge]]:
    ids = _ids(n)
    nodes = [Node(id=s) for s in ids]
    edges = [Edge(rng.choice(ids), rng.choice(ids)) for _ in range(rng.randint(0, n * 2))]
    return nodes, edges


@pytest.mark.parametrize("seed", SEEDS)
def test_render_is_deterministic(seed):
    rng = random.Random(seed)
    nodes, edges = _graph(rng, rng.randint(0, 12))
    assert render(nodes, edges).tobytes() == render(nodes, edges).tobytes()


@pytest.mark.parametrize("seed", SEEDS)
def test_nodes_never_overlap(seed):
    for n in range(2, 41):
        positions, r = layout(_ids(n))
        points = list(positions.values())
        assert len(points) == n
        for i in range(n):
            for j in range(i + 1, n):
                assert math.dist(points[i], points[j]) > 2 * r - 1e-9


@pytest.mark.parametrize("seed", SEEDS)
def test_nodes_stay_on_the_canvas(seed):
    rng = random.Random(seed)
    n = rng.randint(1, 40)
    positions, r = layout(_ids(n))
    w, h = image_size(n)
    for pos in positions.values():
        x0, y0, x1, y1 = node_box(pos, r)
        assert x0 >= 0 and x1 <= w
        assert y0 >= 0 and y1 <= h


def test_image_size_is_bounded_and_grows():
    assert image_size(0) == (420, 420)
    sizes = [image_size(n)[0] for n in range(0, 200)]
    assert all(a <= b for a, b in pairwise(sizes))


def test_edges_to_unknown_nodes_are_ignored():
    nodes = [Node("a"), Node("b"), Node("c")]
    known = [Edge("a", "b")]
    with_ghosts = [*known, Edge("a", "zzz"), Edge("zzz", "b")]
    assert render(nodes, known).tobytes() == render(nodes, with_ghosts).tobytes()


@pytest.mark.parametrize("seed", range(12))
def test_something_is_drawn_for_a_nonempty_graph(seed):
    rng = random.Random(seed)
    nodes, edges = _graph(rng, rng.randint(1, 8))
    img = render(nodes, edges)
    assert img.getpixel((0, 0)) == BACKGROUND
    blank = Image.new("RGB", img.size, BACKGROUND)
    assert img.tobytes() != blank.tobytes()


def test_the_image_is_all_background_when_there_are_no_nodes():
    img = render([], [])
    assert img.tobytes() == Image.new("RGB", image_size(0), BACKGROUND).tobytes()
