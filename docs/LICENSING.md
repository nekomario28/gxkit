# Licensing

## Decision

**The code is MIT.** Every published package (`gxcore` and each `*gx` tool)
declares `License-Expression: MIT` (SPDX, PEP 639) and ships its `LICENSE` file
in the wheel and sdist.

## Why MIT, and not Apache-2.0

Both are permissive and fine here. The trade-off:

| | MIT | Apache-2.0 |
| --- | --- | --- |
| Simplicity | a single short text | adds `NOTICE`, change-notice duties |
| Patent grant | none stated | explicit grant + retaliation clause |
| Enterprise adoption | accepted | often preferred by legal teams |
| Compatibility | maximal (can be folded into GPLv2/v3 etc.) | GPLv3 yes, GPLv2 no |
| Fit here | matches the ecosystem (ManimGX, moderngl, numpy, Pillow are permissive/MIT-style) | some infrastructure projects prefer it |

The whole point of `gxkit` is that other agents and tools pick up the `inspect`
contract; the cheapest path to that is the least bureaucratic license. There are
no patents involved and the dependency set is permissive, so MIT loses nothing
material. **If this later becomes a company product where an explicit patent
grant matters, switch to Apache-2.0** — it is a one-line change per package plus
a `NOTICE`.

The *contract* itself — the problem-code / severity / exit-code / storyboard
shape described in [`BUILDING.md`](BUILDING.md) — is an idea, and ideas are not
licensed. Anyone may implement it; the MIT code is a reference.

## Dependency licenses (why MIT is compatible)

| dependency | license | used by |
| --- | --- | --- |
| Pillow | HPND (permissive) | gxcore, levelgx, flowgx, authzgx, depsgx, schemagx, docgx, protogx, shadergx |
| matplotlib | PSF-based (BSD-compatible) | chartgx |
| numpy | BSD-3-Clause | chartgx, shadergx |
| moderngl | MIT | shadergx |
| glcontext | MIT | shadergx (via moderngl) |
| pytest | MIT | development only |

No copyleft dependency is linked, so no obligation forces a different license.

At runtime `shadergx` uses the system's GL/EGL (Mesa), which is not linked into
the package.

## Acknowledgements

The design is a generalisation of patterns others established:

- **[ManimGX](https://manimgx.academa.ai/)** (Academa, MIT) — the `inspect`
  command: render without video, report layout problems, exit 1, write a
  storyboard. `gxkit` applies that shape beyond animation.
- **[ismail](https://github.com/newsbubbles/ismail)** — the `AGENTS.md`
  convention of "the agent does the installing" and "their words, not ours".
- **[CLI-Anything](https://github.com/HKUDS/CLI-Anything)** — the survey of what
  agent-native tooling already wraps.
- **d2 / mermaid / vlmkit-anim** — diagram tooling whose place `gxkit` does not
  try to take.
- **Inigo Quilez** (<https://iquilezles.org/articles/>) — raymarching / signed
  distance functions and the cosine palette. The hero figure uses these
  *techniques*; its code is original.
