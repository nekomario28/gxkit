"""The domains the hero draws — read from the packages, never written down.

A hardcoded "ten domains" outlives the tenth tool; this repository has sixteen and
the hero said ten. So the scene asks this module, and this module asks the
filesystem. `packages/hero_manifest.json` records what was rendered, and a test
refuses a scene that has been edited without being drawn again.

Plain Python on purpose: the test that guards it cannot import `manimgx`.
"""

from __future__ import annotations

import math
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]

#: One hue per domain, readable on the hero's dark background, and none of them
#: green: the fixed cube has to be the only green in the picture. Length is
#: checked against the domains, so a new tool cannot slip in with a borrowed
#: colour.
PALETTE = [
    "#2563eb",
    "#0891b2",
    "#0369a1",
    "#0ea5e9",
    "#38bdf8",
    "#6366f1",
    "#7c3aed",
    "#a21caf",
    "#db2777",
    "#e11d48",
    "#dc2626",
    "#ea580c",
    "#f59e0b",
    "#facc15",
    "#ca8a04",
    "#a16207",
]

#: Counts as words, for the subtitle. A count outside this map is spelled as a
#: number, which is a worse sentence and never wrong.
_WORDS = {
    10: "ten",
    11: "eleven",
    12: "twelve",
    13: "thirteen",
    14: "fourteen",
    15: "fifteen",
    16: "sixteen",
    17: "seventeen",
    18: "eighteen",
    19: "nineteen",
    20: "twenty",
    21: "twenty-one",
    22: "twenty-two",
    23: "twenty-three",
    24: "twenty-four",
}

#: The one colour that means "checked and fixed". Kept out of `PALETTE` on
#: purpose: with other greens in the ring, the beat is invisible.
FIXED = "#22c55e"

#: Measured, not chosen. With the camera at 40° elevation the ring projects to an
#: ellipse whose minor axis is 0.81 of its major one — at the 62° the hero used
#: first it was 0.49, which is why sixteen cubes half a cube-width apart *looked*
#: like they overlapped: their centres were 1.17 units apart on the ring and only
#: 0.58 apart on screen, against a cube whose silhouette is `sqrt(3) * side` wide.
#: (`docs/hero/gxkit_hero.py` records how to re-measure: four cubes at the compass
#: points, read their pixel centres.)
SQUASH = 0.81

#: The ring's radius, in scene units. Measured: at radius 3.0 with cubes of 0.44
#: the outermost pixel sits about 12% inside a 720x720 frame, at every elevation
#: tried (the major axis does not change with `phi`).
RADIUS = 3.0

#: Screen spacing between neighbouring cubes, divided by the cube's 3D diagonal.
#: Above 1 the cubes cannot intersect; the margin is what stops them *looking*
#: crowded once perspective, the depth wave and antialiasing are counted.
CROWDING = 1.25

#: A cube smaller than this reads as a speck, and the count needs a second ring
#: rather than a thinner one.
MIN_SIDE = 0.22
MAX_SIDE = 0.5

#: Measured from the render at 720x720: three scene units of ring radius are 219
#: pixels of projected major axis, so 73 px per unit, and the frame's half-height is
#: 360 px.
PX_PER_UNIT = 73.0
FRAME_HALF_PX = 360.0

#: The band the title and subtitle occupy at a 720x720 render, measured: the
#: subtitle's descenders end at 155 px and the cube tops were also at 155 px — the
#: text ran through the ring. 190 leaves a visible gap.
TEXT_BAND_PX = 190.0


def geometry(count: int) -> tuple[float, float, float, float]:
    """`(radius, side, depth, drop)` for `count` cubes around the core.

    Derived from the count, so a seventeenth domain cannot quietly squeeze the
    ring. Two budgets are kept, both measured rather than chosen:

    * **across the ring** — the spacing stays `CROWDING` cube-diagonals wide *on
      screen* (`SQUASH` is the projection's flattening), which is what an earlier
      version got wrong: 1.25 diagonals in 3D became 0.8 on screen and the cubes
      looked like they intersected;
    * **above the ring** — the top of the ring clears the title and subtitle band,
      or the ring is dropped along the screen's vertical until it does. The text is
      drawn in frame space, so a ring that grows upward walks into it.

    A count that cannot be drawn inside both budgets is refused here rather than
    rendered crowded.
    """
    if count < 1:
        raise ValueError("a ring needs at least one cube")
    chord = 2 * RADIUS * math.sin(math.pi / count)
    side = min(MAX_SIDE, chord * SQUASH / (CROWDING * math.sqrt(3)))
    if side < MIN_SIDE:
        raise ValueError(
            f"{count} cubes cannot be drawn uncrowded on one ring: each would be "
            f"{side:.3f} units across, below the {MIN_SIDE} floor. Two rings, or a "
            "wider camera, is the fix — not a tighter squeeze"
        )
    # The wave runs along the camera's view axis, so it changes depth without
    # changing where a cube lands on screen: a wave across the screen is what
    # closes the gap the spacing above was computed to keep open.
    depth = 0.15 * chord

    band = (FRAME_HALF_PX - TEXT_BAND_PX) / PX_PER_UNIT  # scene units above centre
    reach = RADIUS * SQUASH + side * math.sqrt(3) / 2
    if reach - band > RADIUS * SQUASH:
        raise ValueError(
            f"{count} cubes leave no room for the title: the ring reaches "
            f"{reach:.2f} units above its centre and only {band:.2f} are free"
        )
    return RADIUS, side, depth, min(0.0, band - reach)


def spacing(count: int) -> tuple[float, float]:
    """`(screen spacing, cube diagonal)` for a count, for the test to hold to."""
    _radius, side, _depth, _drop = geometry(count)
    chord = 2 * RADIUS * math.sin(math.pi / count)
    return chord * SQUASH, side * math.sqrt(3)


def domains() -> list[str]:
    """Every tool, from the packages that declare one."""
    return sorted(
        path.name
        for path in (ROOT / "packages").iterdir()
        if (path / "pyproject.toml").exists() and path.name not in {"gxcore", "gxkit"}
    )


def colours() -> list[str]:
    """One colour per domain, in domain order."""
    names = domains()
    return [PALETTE[index % len(PALETTE)] for index in range(len(names))]


def subtitle() -> str:
    count = len(domains())
    return f"one core \u00b7 {_WORDS.get(count, count)} domains \u00b7 inspect, then ship"
