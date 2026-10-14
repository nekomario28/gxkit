#!/usr/bin/env python3
"""Render gxkit's hero image: a trefoil knot, raymarched — math, not art.

The object is the (2,3) torus knot, `C(t) = ((2+cos(1.5t))cos t, (2+cos(1.5t))sin t,
sin(1.5t))`. The picture is a distance field over that curve, sphere-traced on
the GPU by gxkit's own `shadergx`, shaded with a Lambert term plus a rim light
and coloured by position along the knot. Deterministic: same script, same image.

References — techniques, not copied code:

* Raymarching / sphere tracing, signed distance functions, and the cosine
  palette `a + b·cos(2π(c·t + d))`: Inigo Quilez, <https://iquilezles.org/articles/>
  ("Raymarching SDFs", "Palettes").
* The (2,3) torus-knot parametrisation: standard (see "Torus knot").
* Distance to a parametric curve by sampling its segments: a standard
  approximation of the curve's distance field.

All code here is original; only these published techniques are used.

Needs a GL context (Mesa/EGL or a GPU), because it renders through `shadergx`:

    uv run python scripts/make_hero3d.py   # writes docs/assets/hero-3d.png
"""

from __future__ import annotations

import pathlib

from shadergx import Shader
from shadergx.render import render_image

OUT = pathlib.Path(__file__).resolve().parents[1] / "docs" / "assets" / "hero-3d.png"

FRAGMENT = r"""
const float PI = 3.14159265;
const int NS = 128;

vec3 knot(float t) {
    float ph = 1.5 * t;
    float ring = 2.0 + cos(ph);
    return vec3(ring * cos(t), ring * sin(t), sin(ph));
}

float segdist(vec3 p, vec3 a, vec3 b, out float h) {
    vec3 pa = p - a, ba = b - a;
    h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
    return length(pa - ba * h);
}

/* distance to the tube, and how far along the knot the nearest point is */
float map(vec3 p, out float along) {
    float best = 1e9, bt = 0.0;
    for (int i = 0; i < NS; i++) {
        float t0 = 4.0 * PI * float(i) / float(NS);
        float t1 = 4.0 * PI * float(i + 1) / float(NS);
        float h;
        float d = segdist(p, knot(t0), knot(t1), h);
        if (d < best) { best = d; bt = t0 + h * (t1 - t0); }
    }
    along = bt;
    return best - 0.26;   // tube radius
}

void main() {
    vec2 q = 2.0 * uv - 1.0;
    q.x *= u_resolution.x / u_resolution.y;
    vec3 ro = vec3(0.0, -0.4, -9.0);
    vec3 rd = normalize(vec3(q, 1.95));

    float t = 0.0, hit = -1.0, al = 0.0;
    for (int i = 0; i < 150; i++) {
        float alx;
        float d = map(ro + rd * t, alx);
        if (d < 0.0018) { hit = t; al = alx; break; }
        t += max(d, 0.002);
        if (t > 16.0) break;
    }

    vec3 col = vec3(0.043, 0.063, 0.125);   // dark background
    if (hit > 0.0) {
        vec3 p = ro + rd * hit;
        vec2 e = vec2(0.0025, 0.0);
        float ax;
        float d0 = map(p, ax);
        vec3 n = normalize(vec3(map(p + e.xyy, ax) - d0,
                                map(p + e.yxy, ax) - d0,
                                map(p + e.yyx, ax) - d0));
        vec3 l = normalize(vec3(0.5, 0.6, -0.7));
        float diff = clamp(dot(n, l), 0.0, 1.0);
        float amb = 0.34 + 0.20 * n.y;
        float rim = pow(1.0 - clamp(dot(n, -rd), 0.0, 1.0), 3.5);
        vec3 base = 0.5 + 0.5 * cos(6.28318 * (vec3(0.0, 0.33, 0.67) + al / (4.0 * PI)));
        col = base * (amb + 0.82 * diff) + vec3(0.45, 0.65, 1.0) * rim * 0.6;
    }
    fragColor = vec4(col, 1.0);
}
"""


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    render_image(Shader(fragment=FRAGMENT, size=(1000, 1000))).save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
