"""The domains the hero draws — read from the packages, never written down.

A hardcoded "ten domains" outlives the tenth tool; this repository has sixteen and
the hero said ten. So the scene asks this module, and this module asks the
filesystem. `packages/hero_manifest.json` records what was rendered, and a test
refuses a scene that has been edited without being drawn again.

Plain Python on purpose: the test that guards it cannot import `manimgx`.
"""

from __future__ import annotations

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

#: The one colour that means "checked and fixed". Kept out of `PALETTE` on
#: purpose: with other greens in the ring, the beat is invisible.
FIXED = "#22c55e"

_WORDS = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
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
}


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
