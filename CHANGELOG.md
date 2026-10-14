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

### Changed
- mypy runs in `--strict`; `ruff format --check` is a CI gate; a macOS leg was
  added to the test matrix.

### Tests
- `gxcore.graph` is cross-checked against NetworkX and `gxcore.geometry` /
  `gxcore.layout` against Shapely on random inputs; a GLSL corpus pins the
  surface `shadergx` claims to support; one CLI contract test per tool.

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
