"""Cross-check the hand-rolled bounding-box maths against Shapely.

`gxcore.geometry` decides whether a label overlaps another, whether it is cut
off, and where a storyboard box goes. A quiet off-by-one here is a wrong verdict
on someone's artifact, so every function is compared against Shapely on random
rectangles — the reference implementation, not a second copy of the same idea.
"""

from __future__ import annotations

import random

import pytest
from gxcore import geometry as geo
from gxcore import layout
from gxcore.layout import TextBox
from shapely.geometry import box
from shapely.ops import unary_union

SEEDS = range(20, 44)
STEPS = 200


def _box(rng: random.Random) -> tuple[float, float, float, float]:
    x0 = rng.uniform(0.0, 100.0)
    y0 = rng.uniform(0.0, 100.0)
    return (x0, y0, x0 + rng.uniform(0.0, 60.0), y0 + rng.uniform(0.0, 60.0))


@pytest.mark.parametrize("seed", SEEDS)
def test_area_matches_shapely(seed):
    rng = random.Random(seed)
    for _ in range(STEPS):
        b = _box(rng)
        assert geo.area(b) == pytest.approx(box(*b).area, abs=1e-9)


@pytest.mark.parametrize("seed", SEEDS)
def test_overlap_matches_shapely(seed):
    rng = random.Random(seed)
    for _ in range(STEPS):
        a, b = _box(rng), _box(rng)
        assert geo.overlap(a, b) == pytest.approx(box(*a).intersection(box(*b)).area, abs=1e-9)


@pytest.mark.parametrize("seed", SEEDS)
def test_coverage_matches_shapely(seed):
    rng = random.Random(seed)
    for _ in range(STEPS):
        a, b = _box(rng), _box(rng)
        aa = box(*a)
        inter = aa.intersection(box(*b)).area
        ref = 0.0 if aa.area == 0 else inter / aa.area
        assert geo.covered(a, b) == pytest.approx(ref, abs=1e-9)


@pytest.mark.parametrize("seed", SEEDS)
def test_union_matches_shapely(seed):
    rng = random.Random(seed)
    for _ in range(STEPS // 4):
        boxes = [_box(rng) for _ in range(rng.randint(0, 12))]
        got = geo.union(boxes)
        if not boxes:
            assert got is None
            continue
        assert got is not None
        ref = unary_union([box(*b) for b in boxes]).bounds
        assert got == pytest.approx(ref, abs=1e-9)


def _pair_fraction(a, b) -> float:
    """The fraction of the *smaller* box that is covered, which is what the rule says.

    The reference used `min(inter / aa, inter / bb)` — the fraction of the *larger* —
    so it agreed with an implementation that reported a small box entirely inside a
    big one as no collision at all. A reference that mirrors the code proves only
    that the code is self-consistent.
    """
    aa, bb = box(*a), box(*b)
    if aa.area == 0 or bb.area == 0:
        return 0.0
    inter = aa.intersection(bb).area
    return max(inter / aa.area, inter / bb.area)


def _covered_ref(a, b) -> float:
    aa = box(*a)
    return 0.0 if aa.area == 0 else aa.intersection(box(*b)).area / aa.area


@pytest.mark.parametrize("seed", SEEDS)
def test_intersecting_pairs_matches_shapely(seed):
    rng = random.Random(seed)
    for _ in range(STEPS // 4):
        boxes = [_box(rng) for _ in range(rng.randint(0, 10))]
        frac = rng.uniform(0.0, 0.9)
        got = {(i, j) for i, j, _ in geo.intersecting_pairs(boxes, min_fraction=frac)}
        want = {
            (i, j)
            for i in range(len(boxes))
            for j in range(i + 1, len(boxes))
            if _pair_fraction(boxes[i], boxes[j]) >= frac
        }
        assert got == want


@pytest.mark.parametrize("seed", SEEDS)
def test_clipped_matches_shapely(seed):
    rng = random.Random(seed)
    for _ in range(STEPS):
        b, canvas = _box(rng), _box(rng)
        tol = rng.uniform(0.0, 5.0)
        slack = box(canvas[0] - tol, canvas[1] - tol, canvas[2] + tol, canvas[3] + tol)
        assert (geo.clipped(b, canvas, tol) != []) == (not slack.covers(box(*b)))


def _items(rng: random.Random, n: int) -> list[TextBox]:
    return [
        TextBox(role="label", text=f"t{i}", bbox=_box(rng), fontsize=rng.uniform(5.0, 14.0))
        for i in range(n)
    ]


@pytest.mark.parametrize("seed", SEEDS)
def test_layout_check_matches_shapely(seed):
    rng = random.Random(seed)
    for _ in range(STEPS // 4):
        items = _items(rng, rng.randint(0, 8))
        canvas = _box(rng)
        tol = rng.uniform(0.0, 4.0)
        codes = [p.code for p in layout.check(items, canvas, min_fontsize=8.0, tol=tol)]

        slack = box(canvas[0] - tol, canvas[1] - tol, canvas[2] + tol, canvas[3] + tol)
        want_small = sum(1 for it in items if it.fontsize is not None and it.fontsize < 8.0)
        want_clipped = sum(1 for it in items if not slack.covers(box(*it.bbox)))
        want_overlap = sum(
            1
            for i in range(len(items))
            for j in range(i + 1, len(items))
            if _covered_ref(items[i].bbox, items[j].bbox) > 0.35
            or _covered_ref(items[j].bbox, items[i].bbox) > 0.35
        )

        assert codes.count("small-text") == want_small
        assert codes.count("clipped-text") == want_clipped
        # `check` reports a collision when *either* box is substantially inside
        # the other (`covered(a,b) > f or covered(b,a) > f`), which is the same
        # condition as a pair fraction `> f`.
        assert codes.count("text-overlap") == want_overlap


@pytest.mark.parametrize("seed", SEEDS)
def test_the_grid_finds_exactly_the_pairs_the_rule_defines(seed):
    """The overlap check is bucketed now, and bucketing must not change the *answer*.

    Compared against the double-loop rule on the same random boxes, including the shapes
    the grid has to special-case: boxes far larger than the middle one (which cover more
    cells than a candidate scan is worth) and boxes outside the canvas. Measured, leaving
    an oversized box out of the grid entirely lost real collisions.
    """
    from gxcore.geometry import covered
    from gxcore.layout import TextBox, check

    rng = random.Random(seed)
    for _ in range(6):
        items = []
        for i in range(rng.randint(0, 40)):
            x, y = rng.uniform(-50, 500), rng.uniform(-50, 400)
            width, height = rng.choice([5, 60, 300]), rng.choice([5, 24, 200])
            items.append(TextBox(f"b{i}", f"t{i}", (x, y, x + width, y + height), 12.0))
        want = 0
        for a in range(len(items)):
            for b in range(a + 1, len(items)):
                x, y = items[a], items[b]
                if x.text.strip() == y.text.strip() and x.bbox == y.bbox:
                    continue
                if max(covered(x.bbox, y.bbox), covered(y.bbox, x.bbox)) >= 0.35:
                    want += 1
        got = sum(
            1
            for problem in check(items, (0.0, 0.0, 500.0, 400.0))
            if problem.code == "text-overlap"
        )
        assert got == want, (len(items), got, want)
