# Changelog

Package versions are per-package (see each `pyproject.toml`); the repository tag
is a snapshot. Format: [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- `gxkit` umbrella: `gxkit inspect <file>` (detect and route), `gxkit tools`,
  `gxkit codes`.
- `.gxkit.toml` config: ignore a code or change its severity.
- A reusable GitHub Action (`uses: nekomario28/gxkit@vX.Y.Z`).
- `docs/RELEASING.md`; PyPI metadata and a `gxcore` version pin.
- `scripts/check.sh` — one command that runs every gate CI runs.
- **Baselines** (`inspect --baseline` / `--write-baseline`): a stored report makes
  a run a diff (new / fixed / unchanged) that fails only on new errors.

### Changed
- mypy runs in `--strict`; `ruff format --check` is a CI gate; a macOS leg was
  added to the test matrix.
- The coverage gate is **100%** (statements), with `# pragma: no cover` reserved
  for platform/version fallbacks; the full number needs ffmpeg and a GL context,
  which the Ubuntu CI leg installs.
- CI exercises the **published action** itself (clean artifact passes, faulty
  artifact fails), so the action cannot rot untested.

### Tests
- `gxcore.graph` is cross-checked against NetworkX and `gxcore.geometry` /
  `gxcore.layout` against Shapely on random inputs; the domain tools' graph
  reading (`schemagx`, `protogx`) is cross-checked against NetworkX too, as is
  `levelgx`'s one-way grid (reachability, distances, soft-lock).
- `gxcore.diagram`'s layout invariants (determinism, non-overlap, on-canvas)
  are property-tested on random graphs; `docgx`'s reported text boxes are held
  against the pixels actually drawn.
- `gxkit`'s auto-routing is checked against every real example file, not fake
  classes; `chartgx`'s plot classifier against each real plot kind.
- The loader's abnormal cases (missing, directory, syntax error, `sys.exit`,
  raise) and its discovery precedence are pinned.
- A GLSL corpus pins the surface `shadergx` claims to support; `framegx` is
  exercised on every codec ffmpeg offers (H.264, MPEG-4, VP8/VP9, Theora, GIF)
  plus audio, silence and odd dimensions; one CLI contract test per tool.
- Every tool's **storyboard and render** are exercised end to end and asserted
  non-blank — the images a human reviews are not left untested.

### Fixed
- `Shader.assembled` no longer treats a `#version` inside a comment as a real
  directive (which silently dropped the preamble).
- `shadergx` tries the platform-default GL context (and CGL) so it can work on
  macOS instead of only EGL/WGL/GLX.

## [0.1.2] — robustness

### Added
- `framegx` — inspect a rendered animation (black, frozen, wrong length, silent).
- Security note (the loader runs the artifact file).

### Fixed
- A storyboard that cannot be drawn no longer discards the report.
- Iterative cycle detection (no recursion limit); depsgx no longer double-reports
  a self-dependency; shadergx bounds its canvas.

## [0.1.1] — audit

### Added
- SPDX `License-Expression` and a `LICENSE` in every wheel; `docs/LICENSING.md`.
- Direct tests for `gxcore.diagram`, `gxcore.toolkit`, `graph.shortest_path`.

## [0.1.0] — the family

### Added
- `gxcore` and the first tools: `chartgx`, `levelgx`, `flowgx`, `authzgx`,
  `depsgx`, `schemagx`, `docgx`, `protogx`, `shadergx`.
