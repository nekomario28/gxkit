#!/usr/bin/env python3
"""Render a 3D illustration of what `levelgx` actually catches: a soft-lock.

A reachable node from which the goal is *not* reachable. The layout is fixed
(deterministic) and drawn with math — a small layered graph projected in 3D.

    python scripts/make_math_figure.py   # writes docs/assets/softlock-3d.png
"""

from __future__ import annotations

import pathlib

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "docs" / "assets" / "softlock-3d.png"

# node: (xyz, label, colour-key)   colour keys: ok / goal / trap
NODES = {
    "S": ((0.0, 0.0, 0.0), "start", "ok"),
    "A": ((1.0, 0.5, 0.4), "A", "ok"),
    "B": ((1.9, 1.1, 0.8), "B", "ok"),
    "G": ((2.7, 1.7, 1.2), "goal", "goal"),
    "T": ((0.5, 1.6, 1.9), "T", "trap"),
}
EDGES = [("S", "A"), ("A", "B"), ("B", "G"), ("A", "T")]

COLOR = {"ok": "#16a34a", "goal": "#f59e0b", "trap": "#dc2626"}
INK = "#0f172a"


def build() -> None:
    fig = plt.figure(figsize=(8.2, 5.2), dpi=200)
    ax = fig.add_subplot(111, projection="3d")
    ax.set_axis_off()
    ax.view_init(elev=22, azim=-58)
    fig.patch.set_facecolor("#ffffff")

    # edges as 3D arrows
    for a, b in EDGES:
        (x0, y0, z0) = NODES[a][0]
        (x1, y1, z1) = NODES[b][0]
        dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
        ax.quiver(x0, y0, z0, dx, dy, dz, color="#94a3b8", linewidth=1.6,
                  arrow_length_ratio=0.14)

    # nodes
    for xyz, label, kind in NODES.values():
        x, y, z = xyz
        ax.scatter(x, y, z, s=230, color=COLOR[kind], depthshade=False,
                   edgecolor="white", linewidth=1.4, zorder=5)
        ax.text(x, y, z + 0.22, label, color=INK, fontsize=11,
                ha="center", va="bottom", zorder=6)

    # call out the trap
    tx, ty, tz = NODES["T"][0]
    ax.text(tx + 0.15, ty + 0.1, tz + 0.75,
            "reachable, but the goal is\nnot reachable from here",
            color=COLOR["trap"], fontsize=10.5, ha="left", va="bottom")

    ax.set_title("A soft-lock: the player can get in, and cannot get back",
                 color=INK, fontsize=13, pad=0)
    ax.legend(handles=[
        Line2D([], [], marker="o", linestyle="", color=COLOR["ok"], label="can still finish"),
        Line2D([], [], marker="o", linestyle="", color=COLOR["goal"], label="goal"),
        Line2D([], [], marker="o", linestyle="", color=COLOR["trap"], label="soft-lock"),
    ], loc="lower left", frameon=False, fontsize=9.5)

    # a sane 3D box so the projection reads as depth, not flat
    lim = 3.1
    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)
    ax.set_zlim(0, lim)
    ax.set_box_aspect((1, 1, 1))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
