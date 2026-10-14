# Changelog

Package versions are per-package (see each `pyproject.toml`); the repository tag
is a snapshot. Format: [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [0.2.3] — covered, baselined, hardened

See the [v0.2.3 release](https://github.com/nekomario28/gxkit/releases/tag/v0.2.3).

### Added
- `gxcore.graph.strongly_connected_components` (Kosaraju, iterative; cross-checked
  against NetworkX). `depsgx` reports **cyclic groups** and `schemagx` **cyclic
  tables** — the full component, not just one cycle.
- `gxcore.graph.topological_sort` — a build order (cross-checked against
  NetworkX); `depsgx` reports a **build order** and `schemagx` a **create order**
  when the graph is acyclic.
- `scripts/release.py` prints the publish plan in dependency order (`gxcore`
  first, `gxkit-cli` last) and `--check` validates a built `dist/` against the
  `pyproject` files (names, versions, LICENSE, `py.typed`, sdists), pinned by
  tests; `scripts/check.sh --full` runs it.
- `gxkit` umbrella: `gxkit inspect <file>` (detect and route), `gxkit tools`,
  `gxkit codes`.
- `.gxkit.toml` config: ignore a code or change its severity.
- A reusable GitHub Action (`uses: nekomario28/gxkit@vX.Y.Z`).
- `docs/RELEASING.md`; PyPI metadata and a `gxcore` version pin.
- `scripts/check.sh` — one command that runs every gate CI runs.
- `docs/TRACE.md` — a generated table mapping each tool to its module, codes and
  examples (pinned to `scripts/make_trace.py`; it cannot drift).
- `.gitattributes` — text is LF in the repository, binary assets are never
  converted, so a checkout is reproducible across platforms.
- **Baselines** (`inspect --baseline` / `--write-baseline`): a stored report makes
  a run a diff (new / fixed / unchanged) that fails only on new errors.

### Changed
- mypy runs in `--strict`; `ruff format --check` is a CI gate; a macOS leg was
  added to the test matrix.
- Shell scripts are checked with `shellcheck` in `scripts/check.sh` and CI; the
  Action's inspect logic moved to `scripts/inspect_path.sh` so it is lintable and
  unit-tested, and the workflow references the local action with `./`.
- The coverage gate is **100%** (statements), with `# pragma: no cover` reserved
  for platform/version fallbacks; the full number needs ffmpeg and a GL context,
  which the Ubuntu CI leg installs.
- CI exercises the **published action** itself (clean artifact passes, faulty
  artifact fails), so the action cannot rot untested.

### Tests
- **Repository hygiene**: the files a host and a contributor expect exist, the
  `SECURITY.md` states a reporting path and supported versions, every `<img>` in
  the README has `alt` text, and `.gitattributes` pins text to LF.
- **Docs are reachable and linked**: every released version in the `CHANGELOG`
  has a release link, `docs/PLAN.md` names every tool, every `docs/*.md` is
  referenced from somewhere, every internal `#heading` link resolves, and every
  `README` example matches the tool's real output.
- **What each tool ships** is enforced: `README.md`/`AGENTS.md`/`llms.txt`/
  `SKILL.md`/`LICENSE`, a `SKILL.md` name matching the tool, and only that tool's
  own codes named in its docs; the `CODEBOOK` keys must equal the tools plus
  `gxcore`; the README action example may only use declared inputs.
- **The committed evidence is current**: the architecture SVG equals its
  generator, the levelgx storyboard equals a fresh render (pixel-wise), and
  `docs/TRACE.md` equals its generator; each `llms.txt` names its tool, mentions
  `inspect`, and has an install line.
- **Packaging hygiene**: every package ships `py.typed`, every `LICENSE` equals
  the root, every `__all__` name resolves, and `docs/LICENSING.md`'s dependency
  table matches what the source actually imports.
- **Documented example output is checked against the tools**: every root/`per-tool
  README` example is run and its `inspect:` counts and each shown `[n] severity
  code` must match (it caught five stale examples).
- **Package metadata is checked for the whole family**: `requires-python`,
  license, URL keys and the one command per package, plus the `gxcore` pin range
  covering `gxcore`'s own version. The README's stated domain count is checked
  against the registry.
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
- The `CHANGELOG` sections for 0.2.3 and 0.1.x had no link to their release.
- `docs/LICENSING.md`'s dependency table listed the wrong packages (Pillow was
  missing `chartgx` and `framegx`; numpy wrongly credited `chartgx`).
- `docgx` and `protogx` were missing `AGENTS.md`, though the README and
  `PLAN.md` promise every tool ships it; added, and a guard now enforces the
  required per-tool files.
- The architecture figure's own text said "nine inspect tools" after the tenth
  tool landed; the count is now derived from the tool list, and a test pins the
  committed SVG to the generator so a stale label cannot survive again.
- The reusable Action no longer reports success on a directory with no `*.py`
  artifacts, or on a path that does not exist — an empty gate is a failure.
- `Shader.assembled` no longer treats a `#version` inside a comment as a real
  directive (which silently dropped the preamble).
- `shadergx` tries the platform-default GL context (and CGL) so it can work on
  macOS instead of only EGL/WGL/GLX.

## [0.2.2] — 100% covered, and baselines

See the [v0.2.2 release](https://github.com/nekomario28/gxkit/releases/tag/v0.2.2).

## [0.2.1] — strict everywhere, references checked

See the [v0.2.1 release](https://github.com/nekomario28/gxkit/releases/tag/v0.2.1).

## [0.2.0] — the umbrella, config, codes, a CI action

See the [v0.2.0 release](https://github.com/nekomario28/gxkit/releases/tag/v0.2.0).

## [0.1.2] — robustness

See the [v0.1.2 release](https://github.com/nekomario28/gxkit/releases/tag/v0.1.2).

### Added
- `framegx` — inspect a rendered animation (black, frozen, wrong length, silent).
- Security note (the loader runs the artifact file).

### Fixed
- A storyboard that cannot be drawn no longer discards the report.
- Iterative cycle detection (no recursion limit); depsgx no longer double-reports
  a self-dependency; shadergx bounds its canvas.

## [0.1.1] — audit

See the [v0.1.1 release](https://github.com/nekomario28/gxkit/releases/tag/v0.1.1).

### Added
- SPDX `License-Expression` and a `LICENSE` in every wheel; `docs/LICENSING.md`.
- Direct tests for `gxcore.diagram`, `gxcore.toolkit`, `graph.shortest_path`.

## [0.1.0] — the family

See the [v0.1.0 release](https://github.com/nekomario28/gxkit/releases/tag/v0.1.0).

### Added
- `gxcore` and the first tools: `chartgx`, `levelgx`, `flowgx`, `authzgx`,
  `depsgx`, `schemagx`, `docgx`, `protogx`, `shadergx`.
