#!/usr/bin/env python3
"""Generate the README architecture figure as a deterministic SVG.

Repo-owned and reproducible: no hosted service, no CLI to install. Layout is
math — the tools sit on a circle at evenly spaced angles with evenly spaced
hues, so the picture is the data.

    python scripts/make_readme_figure.py   # writes docs/assets/architecture.svg
"""

from __future__ import annotations

import colorsys
import math
import pathlib

OUT = pathlib.Path(__file__).resolve().parents[1] / "docs" / "assets" / "architecture.svg"

W, H = 1040, 620
BG = "#ffffff"
PANEL = "#f1f5f9"
INK = "#0f172a"
MUTED = "#64748b"
CORE = "#0f172a"
EDGE = "#cbd5e1"

# name, what it inspects, the headline problem code
TOOLS = [
    ("chartgx", "matplotlib charts", "truncated-baseline"),
    ("docgx", "pages / slides", "clipped-text"),
    ("levelgx", "game levels", "soft-lock"),
    ("flowgx", "state machines", "no-exit"),
    ("protogx", "protocols", "unhandled-message"),
    ("depsgx", "module graphs", "layer-violation"),
    ("schemagx", "schemas", "cyclic-foreign-key"),
    ("authzgx", "permissions", "escalation"),
    ("shadergx", "shaders", "black-output"),
    ("framegx", "animations", "frozen"),
    ("apigx", "apis", "unauthenticated-mutation"),
]


def hue(i: int, n: int) -> str:
    h = (i / n) % 1.0
    r, g, b = colorsys.hls_to_rgb(h, 0.42, 0.62)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build() -> str:
    cx, cy, R = 712.0, 320.0, 232.0
    bw, bh = 140.0, 58.0

    p: list[str] = []
    p.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" '
        f'aria-labelledby="t d" font-family="Inter,Segoe UI,Helvetica,Arial,sans-serif">'
    )
    p.append(f'<title id="t">gxkit: one shared core, {len(TOOLS)} inspect tools</title>')
    p.append(
        f'<desc id="d">gxcore is the shared review loop. {len(TOOLS)} tools, one per '
        "artifact domain, each turn an artifact into problems with stable codes, "
        "an exit code and a storyboard.</desc>"
    )
    p.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')

    # ---- left: the inspect loop ------------------------------------------- #
    p.append(f'<rect x="24" y="24" width="360" height="{H - 48}" rx="16" fill="{PANEL}"/>')
    p.append(
        f'<text x="48" y="66" font-size="19" font-weight="700" fill="{INK}">The inspect loop</text>'
    )
    p.append(
        f'<text x="48" y="90" font-size="13" fill="{MUTED}">an agent closes it on its own</text>'
    )

    steps = [
        ("1", "Write the artifact as code"),
        ("2", "inspect \u2192 problems + codes"),
        ("3", "Fix, then inspect again"),
        ("4", "Exit 1 on error \u2192 ship"),
    ]
    y = 116.0
    for i, (n, label) in enumerate(steps):
        p.append(
            f'<rect x="48" y="{y}" width="300" height="62" rx="11" fill="#ffffff" stroke="{EDGE}"/>'
        )
        p.append(f'<circle cx="76" cy="{y + 31}" r="14" fill="{CORE}"/>')
        p.append(
            f'<text x="76" y="{y + 36}" font-size="14" font-weight="700" '
            f'fill="#ffffff" text-anchor="middle">{n}</text>'
        )
        p.append(f'<text x="104" y="{y + 37}" font-size="14.5" fill="{INK}">{esc(label)}</text>')
        if i < len(steps) - 1:
            p.append(
                f'<line x1="76" y1="{y + 62}" x2="76" y2="{y + 88}" '
                f'stroke="{EDGE}" stroke-width="2"/>'
            )
            p.append(
                f'<path d="M71 {y + 86} L76 {y + 95} L81 {y + 86}" fill="none" '
                f'stroke="{EDGE}" stroke-width="2"/>'
            )
        y += 88

    p.append(
        f'<text x="48" y="{H - 58}" font-size="12.5" fill="{MUTED}">'
        "every problem: a stable code, a severity,</text>"
    )
    p.append(
        f'<text x="48" y="{H - 40}" font-size="12.5" fill="{MUTED}">'
        "and a storyboard image as evidence</text>"
    )

    # ---- right: the core and its tools ------------------------------------ #
    p.append(
        f'<text x="712" y="44" font-size="15" fill="{MUTED}" text-anchor="middle">'
        f"one core \u00b7 {len(TOOLS)} domains</text>"
    )

    pos = []
    for i in range(len(TOOLS)):
        a = -math.pi / 2 + 2 * math.pi * i / len(TOOLS)
        pos.append((cx + R * math.cos(a), cy + R * math.sin(a)))

    # edges first, so nodes sit on top
    for x, y2 in pos:
        p.append(
            f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{x:.1f}" y2="{y2:.1f}" '
            f'stroke="{EDGE}" stroke-width="1.4"/>'
        )

    # core
    p.append(
        f'<rect x="{cx - 92:.0f}" y="{cy - 62:.0f}" width="184" height="124" '
        f'rx="16" fill="{CORE}"/>'
    )
    p.append(
        f'<text x="{cx:.0f}" y="{cy - 26:.0f}" font-size="25" font-weight="700" '
        f'fill="#ffffff" text-anchor="middle">gxcore</text>'
    )
    for k, line in enumerate(
        [
            "problems \u00b7 severities \u00b7 exit codes",
            "storyboard \u00b7 graph \u00b7 layout",
            "diagram \u00b7 loading \u00b7 toolkit",
        ]
    ):
        p.append(
            f'<text x="{cx:.0f}" y="{cy + 2 + k * 18:.0f}" font-size="12" '
            f'fill="#cbd5e1" text-anchor="middle">{esc(line)}</text>'
        )

    for i, ((name, what, code), (x, y2)) in enumerate(zip(TOOLS, pos, strict=True)):
        color = hue(i, len(TOOLS))
        left, top = x - bw / 2, y2 - bh / 2
        p.append(
            f'<rect x="{left:.1f}" y="{top:.1f}" width="{bw}" height="{bh}" rx="11" '
            f'fill="#ffffff" stroke="{color}" stroke-width="1.8"/>'
        )
        p.append(f'<circle cx="{left + 16:.1f}" cy="{y2 - 12:.1f}" r="4.5" fill="{color}"/>')
        p.append(
            f'<text x="{left + 27:.1f}" y="{y2 - 8:.1f}" font-size="14.5" '
            f'font-weight="700" fill="{INK}">{name}</text>'
        )
        p.append(
            f'<text x="{left + 16:.1f}" y="{y2 + 9:.1f}" font-size="11.5" '
            f'fill="{MUTED}">{esc(what)}</text>'
        )
        p.append(
            f'<text x="{left + 16:.1f}" y="{y2 + 26:.1f}" font-size="11.5" '
            f'fill="{color}">{esc(code)}</text>'
        )

    p.append("</svg>")
    return "\n".join(p) + "\n"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
