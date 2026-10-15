# Changelog

Package versions are per-package (see each `pyproject.toml`); the repository tag
is a snapshot. Format: [Keep a Changelog](https://keepachangelog.com/).

## Unreleased — reaudit hardening

### Fixed
- A network finding is identified by its own relationship: replacing the unknown
  endpoint of one edge is a new error, not unchanged baseline debt.
- Requested inputs are resolved once before any artifact executes, so an
  artifact's own directory change cannot redirect routing, loading or the
  project configuration to another file.
- Recognised declarations fail closed on their auxiliary collections: environment
  references, pipeline goals and API auth schemes must be lists of names, and a
  non-name member is rejected with its field and index.
- The coverage gate is provable in both directions: an inherited pytest option
  override and a swallowed failing run are both rejected by the named guard.
- A report prints on a console that cannot encode every character it names. A
  message naming an edge arrow on a Windows code page turned a real verdict into
  an input failure; unencodable characters are escaped instead.

### Verification
- `scripts/guard_contracts.py` replays the environment its stubbed commands run
  in and then a failing coverage run, and `scripts/check_mutations.py` carries
  eleven more bounded mutants (39 total) covering these repairs.
- gxcore is staged at 0.6.0 for `convert_names`; changed domain packages and
  gxkit-cli receive patch versions. No release tag or PyPI publication is
  created by this branch.

## Unreleased — inspection correctness hardening

### Fixed
- Artifact exits during import or detection are input failures, never successful
  inspection; directory inspection continues to later files.
- Routing and inspection execute the same module once per invocation and read
  current source rather than stale timestamp-matched bytecode.
- Baselines preserve repeated findings and cron conflict partners. Format 2
  rejects version 1; deliberately recreate accepted debt after reviewing it.
- Malformed collection members are rejected with a field/index, not dropped or
  hidden by another representation's fallback.
- Schedule tuple defaults, empty intervals and non-finite times; seed integer
  validation without truncation; references against empty declarations; API base
  matching at a path boundary.

### Verification
- Setup-handoff and executable coverage-command guards replace token presence.
- Bounded mutation proofs run green controls before restoring named defects in
  disposable copies. Git consumer checks install an immutable revision in fresh
  tool/cache directories and exercise inspection and baseline exit semantics.
- gxcore is staged at 0.5.0, with compatible dependency ranges in consumers;
  changed domain packages and gxkit-cli receive patch versions. No release tag
  or PyPI publication is created by this hardening branch.

## [0.9.1] — publish-readiness audit fixes

See the [v0.9.1 release](https://github.com/nekomario28/gxkit/releases/tag/v0.9.1).

A `publish-readiness-audit` pass over the tree and the full history found no
blockers and turned its two low-severity items into permanent guards.

### Fixed
- **Author attribution.** `gh pr merge --squash` authored one commit with the
  GitHub *profile* display name, so it read `Yuu` instead of `nekomario28`.
  Added a `.mailmap` and a guard that fails on any author outside the allowlist.

### Added (guards)
- `test_authors_are_canonicalised_through_the_mailmap` — a new unattributed
  author must be listed, not silently accepted.
- `test_the_readme_agent_prompt_is_installable` — the README's paste-into-agent
  prompt names `llms.txt`, whose install line must point at a real package.
- `test_the_coverage_floor_names_every_distribution` — `--cov-fail-under=100`
  and the full `--cov=` set must be present in `scripts/check.sh` and CI.
- `test_ffmpeg_bound_modules_are_not_excluded_from_coverage` — a `# pragma: no
  cover` in `framegx`'s ffmpeg-bound modules would turn a missing capability
  back into a silent pass; the 100% floor is what binds it (verified: 62%
  without ffmpeg, 92% without the GL render tests).

## [0.9.0] — crongx, the sixteenth tool

See the [v0.9.0 release](https://github.com/nekomario28/gxkit/releases/tag/v0.9.0).

### Added
- `crongx` — inspect a schedule of timed runs: two runs holding the same
  resource at once, a duplicate run, a negative start or duration, a run that
  never runs; the interval overlap is cross-checked against `gxcore.geometry`.

## [0.8.0] — seedgx, the fifteenth tool

See the [v0.8.0 release](https://github.com/nekomario28/gxkit/releases/tag/v0.8.0).

### Added
- `seedgx` — inspect a random-seed manifest: a stream with no seed, a seed
  outside `0..2**32-1`, two streams sharing a seed, a duplicate stream, a
  non-deterministic manifest.

## [0.7.0] — pipegx, the fourteenth tool

See the [v0.7.0 release](https://github.com/nekomario28/gxkit/releases/tag/v0.7.0).

### Added
- `pipegx` — inspect a build pipeline DAG: a `needs` that names no step, a
  cycle, a duplicate step or artifact, a goal nothing produces; prints the build
  order when the graph is a DAG.

## [0.6.0] — envgx, the thirteenth tool

See the [v0.6.0 release](https://github.com/nekomario28/gxkit/releases/tag/v0.6.0).

### Added
- `envgx` — inspect an environment / config declaration: an undeclared
  reference, a declaration nothing reads, a secret with a default, an unknown
  type, a required variable that also has a default.

## [0.5.0] — netgx, the twelfth tool

See the [v0.5.0 release](https://github.com/nekomario28/gxkit/releases/tag/v0.5.0).

### Added
- `netgx` — inspect a network topology: an edge to an unknown node, a public
  entry that reaches sensitive data, a self-loop, a duplicate edge, an isolated
  node, or no public entry.

### Changed
- `SECURITY.md` states a concrete supported-versions policy (the latest release
  of `gxcore`, every `*gx` tool and `gxkit-cli`; Python 3.10–3.13).

### Tests
- Every tool's `AGENTS.md` must name the tool, mention `inspect` and state the
  exit code; every `SKILL.md` must name at least one of its own codes; the
  `SECURITY.md` policy must name the distributions and the Python range.

### Added
- `chartgx`: `inverted-axis` (warn) — a value axis that grows the wrong way
  (`ylim`/`xlim` reversed), which reads magnitudes upside down.

## [0.4.0] — apigx, the eleventh tool

See the [v0.4.0 release](https://github.com/nekomario28/gxkit/releases/tag/v0.4.0).

### Added
- `apigx` — inspect an HTTP API contract: duplicate routes, a mutation with no
  authentication, a path outside the versioned base, an endpoint documenting no
  error, a deprecated route.

## [0.3.0] — deeper analysis, checked releases

See the [v0.3.0 release](https://github.com/nekomario28/gxkit/releases/tag/v0.3.0).

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
