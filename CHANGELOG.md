# Changelog

Package versions are per-package (see each `pyproject.toml`); the repository tag
is a snapshot. Format: [Keep a Changelog](https://keepachangelog.com/).

## [1.0.0] — first release

See the [v1.0.0 release](https://github.com/nekomario28/gxkit/releases/tag/v1.0.0).

The first published version. Everything below is the same release entry: the
family had repository tags before this, but no distribution had been published,
so no version here is an increment from a released one.

**What 1.0.0 promises** is in [`docs/CONTRACT.md`](docs/CONTRACT.md): problem
codes, severities, exit codes, the JSON report's keys, the CLI shape, baseline
format 2, and Python 3.10–3.13 on Linux, macOS and Windows. Message prose,
problem order, storyboard pixels, the importable Python API and capability-bound
behaviour are explicitly not promised.

### Added

- **Reading the file a project already has**, so a tool can be pointed at what
  exists instead of a transcription:
  - `apigx inspect openapi.json` — an OpenAPI 3 document: paths and methods
    become endpoints, `security` becomes authentication, numeric responses become
    statuses, and the endpoint paths are built in the server's coordinate space.
  - `schemagx inspect schema.sql` — SQL DDL: `CREATE TABLE`, `PRIMARY KEY` and
    `FOREIGN KEY ... REFERENCES` become the same model, and column types are
    compared by family.
  - `flowgx inspect checkout.mmd` — a Mermaid state diagram, or the one
    `stateDiagram` block a Markdown document holds.
  - `chartgx` and `framegx` already read what exists: a plain matplotlib script
    and a rendered video file.
- **`docs/CONTRACT.md`**, the stability promise above, including what the tools
  are not: not a conformance validator, not a check on this repository's own
  format reading, not a runtime or quality oracle.
- **Publication and installation gates**: `scripts/check_publish.py` builds every
  distribution, serves them from a local PEP 503 index and installs the umbrella
  and each tool against it, so a dependency range only a resolver would reject
  fails before anything is published. `scripts/check_consumer.py` installs an
  immutable Git revision in isolated tool/cache directories and runs the
  entrance the README documents, verbatim.
- **A family that inspects itself**: `scripts/self_inspect.py` derives the real
  import and routing graph and runs `depsgx` on it, pinning the layering a shared
  layer cannot express.

### Fixed

**Inspecting nothing and reporting success.** An artifact that exits during
import or detection is an input failure, never a successful inspection; a
directory continues past a broken file; routing and inspection execute a module
once per invocation and read current source rather than stale bytecode; requested
inputs are resolved once before anything executes, so an artifact cannot redirect
the inspection by changing directory; and a report prints on a console that
cannot encode every character it names.

**A verdict that was not the verdict.** Recognised declarations fail closed on
malformed members and auxiliary collections, with the field and index named
instead of a silent fallback to another shape; schedule tuple defaults, empty and
non-finite intervals, seed integer validation, references against explicitly
empty declarations, API base path boundaries, and name collections are explicit
cases.

**Baselines that hid debt.** A finding is identified by a domain-owned stable
identity and its multiplicity is preserved: a replaced cron conflict partner, a
replaced network edge endpoint, and a rotated cycle witness are new findings, not
unchanged debt. Format 2 rejects older baselines and asks for a deliberate
recreation rather than guessing.

**Importers that read less than they claimed.** An importer refuses what it
cannot account for — an unrecognised key in an OpenAPI path item or operation, a
`webhooks` section, a `$ref`, a statement outside the translated SQL, a
composite key, a diagram the machine cannot hold — with its location, rather than
narrowing what it read and reporting success about the rest. Independent review
found five such defects, all reproduced and repaired: an anonymous `security`
alternative read as authenticated (hiding a public mutation), a server path
ignored, an intervening `ALTER` skipped, an omitted reference column invented,
and a `$ref` path item dropped.

**A gate that could not fail.** The coverage guard observes the environment its
executed commands run in and replays a failing run, so an inherited pytest
override and a swallowed failure are both rejected. Setup handoff and the
documented entrance are executed rather than matched as text.

**`depsgx`** reports a cycle witness for every independent cyclic component, not
only the first found.

### Fixed

Two further rounds — a whole-diff review and a coherence sweep over the release
candidate — found six more, all reproduced and repaired:

- `schemagx`: a composite `FOREIGN KEY` whose target was omitted was resolved
  before the child columns were validated, so `FOREIGN KEY (a, b) REFERENCES p`
  kept `a` and silently dropped `b`. The count is validated first.
- `schemagx`: comment stripping was not quote-aware, so a value containing `--`
  (`DEFAULT '--'`) was truncated and the table read as unclosed. Comments are now
  stripped by a quote-aware scanner, and an unterminated comment or literal is
  refused instead of swallowing the rest of the file.
- `apigx`: an operation or path-item `servers` override was accepted and ignored,
  so the endpoint was reported at the document's path rather than the override's.
  An override that changes the path is refused, because the model has one base.
- `apigx`: the base is no longer inferred from the paths' shared prefix. Every
  path shares an inferred prefix by construction, so the value could never fail a
  check while appearing to have judged; no declared server now means no base.
- The umbrella used none of the `reads` declaration it now carries: it told the
  reader to name the tool for a document that is not Python without saying which.
  The registry declares the suffixes, so it names the tool; `gxkit tools --json`
  publishes them.
- `netgx`: `self-loop` and `duplicate-edge` now carry relationship identities, so
  replacing which destination is duplicated is a new finding rather than
  persisted debt at the same source.

### Fixed

A second sweep, over the shared core's own input files, found that the rule the
tools apply to artifacts was not applied to gxcore's inputs:

- `ignore = "soft-lock"` in `.gxkit.toml` was iterated as a string, so it meant
  the eight characters it contains; a severity that was not `error`/`warn`/`info`
  was dropped in silence; and a mistyped key in a tool table sat there looking
  active. All are refused with their field now, and `apply` refuses an invalid
  severity however the `Config` was built.
- A baseline whose `problems` was not a list of records was read as whatever it
  happened to iterate to, so a corrupted baseline reported every finding as fixed
  or new. Its shape is validated with the field and index.
- The test that pinned the old behaviour (`test_invalid_severity_is_ignored`) is
  replaced by one that requires the refusal.

A third sweep, over the tools' checks and the renderer:

- `netgx` reported **nothing at all** for a network that declares no nodes, so
  `inspect: no problems` stood for an empty artifact. It emits `no-nodes`
  (info) as every other tool does for an empty declaration.
- The storyboard's promise — "each located problem boxed and numbered, so the
  text report and the picture agree" — was guarded only by "the image is not
  blank". The box geometry is now a pure function (`gxcore.storyboard.labelled_boxes`)
  and a test asserts, for every tool and every example, that each located problem
  is numbered exactly once and that the number lands on a box drawn from that
  problem's own location. Two mutants (off-by-one numbering, boxing an unlocated
  problem) are killed.

A fourth sweep, over the gates themselves: **a gate that cannot be shown failing
is a log line, not a gate.** Every one is now proven by a mutant.

- `scripts/prepublish_check.py` — the credential and machine-path rule — had no
  test at all: its only red proof was a manual probe. Its rules are a pure
  function with one test per rule now, and the live gate runs inside the suite
  over the tracked tree, so a tracked credential fails the tests rather than only
  the CI step. The samples are assembled from pieces, because a literal sample
  would make the gate fail on its own test file.
- The catalogue covers the gates: the hygiene rules, `release.py::check_dist`
  (LICENSE and unexpected-wheel), `make_trace.py`'s generated column,
  `self_inspect.py`'s sibling rule, and `inspect_path.sh`'s refusal of a
  directory with no artifacts.
- Writing them found a **missing test**: `check_dist` refuses a wheel with no
  `LICENSE`, and nothing proved that check could fire. It has one now.

A fifth sweep asked the cross-tool question: **was a defect fixed in one tool and
left in its siblings?** The answer was yes, four times.

- "Only the first cycle is reported" was fixed for `depsgx` and still present in
  **`authzgx`** (a role-inheritance cycle, error), **`pipegx`** (a `needs` cycle,
  error), **`flowgx`**, **`protogx`** and **`schemagx`**. Two independent cycles
  produced one finding, so a gate passed with the second one present. Measured
  before the fix: `authzgx` reported `role:r1` and not `role:r3`; `pipegx`
  reported `a` and not `c`.
- The rule now has **one owner**, `gxcore.graph.cycle_witnesses(graph)`, returning
  one witness per cyclic component with the component itself. `depsgx`'s inline
  loop is gone, `Schema.cycle()` is gone (its only caller was the check), and all
  six tools identify a cycle finding by its component members, so a witness that
  rotates is the same finding rather than new debt.
- A cross-tool regression asserts the property for all six at once, and one
  mutant per tool plus the shared helper keeps it from coming back in any of them.

A sixth sweep asked whether a reader can look up what they were told. **28
problem codes were missing from the reference documents** that are supposed to
list them:

- `crongx/SKILL.md` and its `llms.txt` never named `non-finite-time`, a code added
  in this release;
- `flowgx` and `gxcore` documented none of the shared layout codes
  (`clipped-text`, `text-overlap`, `small-text`) although flowgx emits them;
- `levelgx/SKILL.md` described three codes in prose and left five uncatalogued;
- `authzgx` and `chartgx` each omitted one.

All are documented now, and `test_every_problem_code_is_documented_for_its_tool`
requires every catalogued code to appear in that tool's `README.md`, `SKILL.md`
and `llms.txt`. `AGENTS.md` is a narrative summary and is deliberately exempt.
A mutant that renames a code out of the docs is killed.

A seventh sweep, over the exit policy every tool shares. It was already guarded —
16 tools × 5 malformed inputs, each required to exit 2 without a traceback — but
the table did not include the case a real audit found in the umbrella:
**`sys.exit(0)` during load**, where an artifact that asks to stop with success
produced a green run from a file nobody inspected. Measured: every tool already
treats it as a load failure, so the two missing kinds are in the table now, and a
mutant that removes the direct tool's `SystemExit` handling is killed.

Writing that mutant exposed a weakness in the test: it asserted only the return
code, so a `SystemExit` escaping the CLI would have surfaced as a confusing
propagating exception rather than the claim it breaks. It now says so explicitly.

An eighth sweep, over the baseline contract for every tool. Accepting an artifact
and re-inspecting it must report nothing new — and each tool supplies its own
finding identities, which is exactly where three real defects were found. The
round trip was exercised for a few tools; it is now asserted for all sixteen,
with a mutant that records an empty baseline and is killed.

### Fixed

Repository hygiene, from a sweep of the repository itself rather than the code:

- The packaging job uploaded the built distributions on every run and nothing
  downloaded them, so **148 artifacts (~53 MB) had accumulated**. They are
  deleted, the upload declares `retention-days: 7`, and a guard requires every
  artifact upload to declare a sensible retention — with a mutant that removes it.
- Sixteen merged local branches, a stale audit worktree and a pruned
  remote-tracking ref were removed; the primary checkout was fast-forwarded from
  the `v0.9.1` commit it had been left on.

### Fixed

- **Eight error findings that can repeat are now identified by the relationship
  they are about**, so replacing one relationship with another is new debt rather
  than unchanged debt: `pipegx.goal-not-produced` (per goal),
  `protogx.unhandled-message` (per message) and `unknown-message` /
  `unknown-state` (per transition), `schemagx.dangling-foreign-key` (per reference
  and missing side), and `authzgx`'s three `dangling-*` (per referrer and missing
  name). The remaining 14 findings that carry no location cannot occur twice in
  one artifact, and `docs/IDENTITY.md` records the single `if`/`except` that makes
  each one true — checked against the source, so the reasons cannot go stale.
- `netgx` reported only the **first** public entry that reaches a sensitive node,
  so a second exposure route was invisible, and the finding was identified by the
  sensitive node alone. Measured: with `a` and `b` both reaching `db`, one finding;
  and changing the entry from `a` to `b` gave `new_errors: 0` under a baseline, so
  the gate passed on a changed exposure route. Every route is reported now, each
  identified by `(entry, sensitive)`.

### Added

- **`docs/IDENTITY.md`** — generated and ratcheted. It lists the error findings
  that carry neither a `target` nor a relationship `identity`, so two of them in
  one artifact share a baseline fingerprint and replacing one with another reads
  as unchanged debt. **24 sites** across nine tools are listed; the count may only
  shrink, and a mutant that removes a target proves the ratchet bites.
- **`chartgx` inspects a chart declared as data**, so a figure can be checked
  without matplotlib and without running anything: `chartgx inspect chart.json`
  reads a figspec model and reports the problems directly. It is the route for a
  chart a model generated, and for reviewing a file you would rather not execute.
  The codes are the same wherever the concept is the same (`truncated-baseline`,
  `empty-chart`, `log-nonpositive`, `no-title`, `no-xlabel`/`no-ylabel`), because
  a finding must not have two names depending on which route produced it; four are
  new because a figure cannot express them (`mismatched-lengths`,
  `non-finite-value`, `two-error-shapes`, `negative-error`).
  A declaration has no storyboard — box numbers are drawn over a figure's
  artists — so the report is printed and the image is skipped with that reason.
- The umbrella lists **every** tool that reads a suffix: `.json` is an OpenAPI
  document to `apigx` and a chart declaration to `chartgx`, so the message names
  both and asks which one is meant, instead of assuming.

### Verification

- 1769 tests, 100% statement coverage, strict mypy, ruff, shellcheck, zizmor and
  a dependency audit; every distribution built, checked with `twine` and against
  its `pyproject`; a public-Git consumer install at an exact revision; and the
  index installation gate.
- A bounded mutation catalogue of 101 named defects, each killed by its intended
  assertion after green controls, running in the local gate and in CI.
- CI runs the suite on Ubuntu 3.10–3.13, Windows and macOS.

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
