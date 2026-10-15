# Building a `*gx` tool

Build the loop an agent can close on its own:

```
write artifact as code  →  inspect (codes + exit code + storyboard)  →  fix  →  inspect  →  ship
```

The reference implementation is **gxkit** (this repository; `gxcore` plus the
`*gx` tools).
Read a tool whose artifact resembles yours before writing a new one — the
patterns are small and copied often.

## 1. Is a new tool worth building? (the checklist)

Answer all five. One "no" usually means stop.

1. **Objective** — the property is right/wrong, not taste. ("Is the goal
   reachable?" yes. "Is the prose good?" no.)
2. **Self-contained** — correctness follows from the artifact itself; no
   external spec or human intent is needed.
3. **Cheaply decidable** — the artifact reduces to a finite / declarative
   structure (a graph, a grid, a set of boxes).
4. **You own the representation** — you define the format the agent writes, so
   you can compute the property exactly instead of guessing from a render.
5. **A mature tool with exit codes does not already exist** — the decisive
   test. Arbitrary code (Rice's theorem) and style linting are already
   saturated by compilers, `ruff`/`eslint`, `spectral`, `tflint`, … Build only
   where a domain's *semantics* are unchecked.

If the artifact is arbitrary code, do not build a general "software linter" —
it is undecidable and over-served. Generalise to a **model** instead
(permission graph, dependency graph, schema, state machine, level grid).

## 2. The contract (non-negotiable)

Every tool ships the same surface, because an agent must not re-learn it:

- a **stable `code`** per problem (`truncated-baseline`, `soft-lock`,
  `escalation`, `cycle`). Agents branch on codes, **never on prose**.
- **severity** `error` / `warn` / `info`; only `error` fails.
- **exit 1** on any error, `0` otherwise.
- **`--json`** — the same report, machine-readable.
- a **storyboard PNG** with a numbered box per located problem, and the numbers
  **matching the text report**.
- a broken input file reports an error, **never a traceback**.
- **`--baseline` / `--write-baseline`** — a stored baseline (`gxcore.baseline`)
  turns a run into a diff: new / fixed / unchanged, failing only on new `error`s.
- `render` to a PNG for the plain picture.

## 3. Structure: one core, thin tools

`gxcore` owns everything identical across tools — do **not** re-implement it:

- `model` / `report` / `cli` / `storyboard` — Problem, Report, severities, the
  `inspect`/`render` commands, `--json`, the number boxes.
- `graph` — reachability, reverse reachability, **traps** (soft-locks),
  `shortest_path`, `find_cycle`, components.
- `layout` — text too small / clipped / overlapping.
- `diagram` — a deterministic node-link renderer.
- `loading` — one convention for loading an artifact from a Python file.
- `toolkit` — `scene_tool(...)` builds `Tool` + `main` from three callables.

A new tool is three things:

```
loader     file    -> artifact
checks     artifact -> [Problem]
renderer   artifact -> PIL.Image
```

`tool.py` is then five lines:

```python
main, TOOL = scene_tool(
    name="schemagx", description="…",
    load=load_schema, inspect=inspect_schema, to_image=render_image,
)
```

### Extraction rule

Move code into `gxcore` **only when a second tool needs it.** `graph`,
`layout`, `loading`, `diagram`, `toolkit` were each extracted only after the
second or third tool made the duplication real. Do not pre-abstract.

## 4. The test convention

A check that cannot fail is decoration. For **every** check, write:

- one test that builds the defect and asserts `(severity, code)` fires;
- one test that asserts a clean artifact stays quiet.

And, per tool, three abuse tests: **malformed input** (empty, syntax error,
`sys.exit()` on import) must exit 2 with a message and never a traceback; a
**property test** over random well-formed artifacts must return a `Report`
not raise; and **lint + types run in CI**, not only by hand.

Beyond that: **cross-check any hand-rolled algorithm** against a reference
library — `gxcore.graph` versus NetworkX on random digraphs, `gxcore.geometry`
and `gxcore.layout` versus Shapely on random rectangles — and keep **one CLI
contract test per tool** (faulty exits 1, honest exits 0, `--json` parses with
an error). A corpus of valid and invalid shaders pins the GLSL surface
`shadergx` claims to support; the domain tools' *reading* of a graph
(`schemagx` cycles/orphans, `protogx` reachability/deadlocks) is cross-checked
against NetworkX the same way; and `framegx` is exercised on every codec ffmpeg
offers (H.264, MPEG-4, VP8/VP9, Theora, GIF), each skipped when the encoder is
absent. Routing is checked against the *real* example files (not fake classes),
and a tool's drawn pixels are held against the boxes it reports.

Use `gxcore.testing` (`assert_fires`, `assert_quiet`, `has`, `codes`). Inject
the defect into a real artifact (a figure, a level, a machine), not a mock.

The family also inspects itself: `scripts/self_inspect.py` derives the real
package graph from the sources and the umbrella's routing table, runs `gxkit` on
it, and requires the layering this repository claims. It lives at the repository
root, so no distribution carries it, and the sibling-dependency rule sits in the
test because two tools sharing a layer is legitimate for `depsgx` to accept.

A presence check is not a gate proof. `scripts/guard_contracts.py` checks the
actual setup handoff and records pytest arguments from trusted shell scripts
with external commands stubbed out. Comments and echo output cannot stand in
for execution. It also replays the environment those commands run in and then a
failing coverage run, because argv evidence alone cannot tell enforcement from a
command whose exit status is discarded: an inherited `--no-cov` and an appended
`|| true` are both mutations the guard must reject. The shell observer runs on
POSIX coverage lanes; Windows still exercises inspector behavior. Real
installation is a separate consumer gate.

`scripts/check_mutations.py` first runs green controls, then restores named
faults in disposable source copies. Rejection counts only when the intended
test assertion fails, not when collection or imports break. It runs in the
local gate and Ubuntu CI. Keep that bounded catalogue with each regression;
it is not an exhaustive proof against arbitrary edits.

The POSIX consumer check in `scripts/check_consumer.py` installs a full Git SHA
in fresh tool/cache directories, verifies direct-URL provenance, then exercises
inspection and baseline exit semantics from outside the workspace. The package
CI job uses its exact checkout revision; a remote URL run additionally checks
that the same revision is publicly retrievable.

## 5. Disciplines that catch real bugs

- **Look at the storyboard image.** Every rendering bug in this project — a
  vertically flipped origin, a numbering that disagreed with the report,
  co-located problems whose boxes hid each other — was invisible in the text
  report and obvious in the picture. When you can view images, view them.
- **Measure exit codes correctly.** `tool … | tail; echo $?` prints `tail`'s
  code; `echo "$(cmd): $?"` runs the substitution first, so `$?` is *its* code.
  Capture `rc=$?` on its own line, immediately after the tool runs.
- **Reproduce before you report a hole.** A failing check may be the
  environment, not the code: "12 collection errors on Python 3.10" turned out to
  be a venv built for another interpreter. Re-run in a clean, authoritative
  environment before you believe a defect.
- **Let the coverage floor bind the optional capabilities.** A test that needs
  ffmpeg or a GL context skips on a runner without it — so make the lines only
  it covers the reason the floor fails when it does. Verified here: without
  ffmpeg `framegx` coverage is 62% and `--cov-fail-under=100` fails; without the
  GL render tests `shadergx` is 92% and fails. Do not add `# pragma: no cover`
  to those lines; that is what turns a missing capability back into a silent
  pass.

## 6. Pitfalls learned from the family

- **Nested boxes.** "Do these two collide?" must ask whether the *smaller* box
  is mostly inside the other. Requiring *both* to be covered misses a small
  label sitting on a large block.
- **Legitimate self-loops.** A self-referential edge (a `manager_id` tree, a
  retry loop) is not a cycle. Exclude self-edges before `find_cycle`, or you
  report trees as faults *and* hide the real cycle behind them.
- **One defect, one code.** When a specialized check owns a case, exclude it
  from the general one. A self-edge is `self-dependency`, not *also* `cycle`;
  two codes for one fault make every count and every gate lie.
- **The optional image must not kill the report.** Compute the report first;
  draw the storyboard best-effort. If drawing fails (no GPU, no font), print the
  report and return its exit code anyway, with a note on stderr.
- **Do not recurse on agent-sized input.** Agent-generated graphs get deep; a
  recursive DFS raises `RecursionError` on a chain of a few thousand. Traverse
  iteratively.
- **Bound what the author chooses.** Any size the artifact sets (canvas pixels,
  iteration counts) needs a ceiling that fails clearly (`bad-size`) instead of an
  OOM.
- **One line per problem.** Collapse compiler logs and multi-line errors; a
  report is a list, and a 40-line stack trace in one item breaks it.
- **A test that always skips is not coverage.** If the hard tests need a
  capability (a GPU, a display), give CI a software fallback (Mesa's software
  GL) so they actually run.
- **Stale core wheel.** In a multi-package workspace, installing one tool reuses
  a cached wheel of the shared core. When the core changes, bump its version, or
  the tool fails at import (`ModuleNotFoundError: gxcore.toolkit`).
- **A checker's cache can lie.** mypy's incremental cache hid two real type
  errors that a fresh CI run caught. Clear it (`rm -rf .mypy_cache`) before
  believing a local `Success`; let CI be the authority.
- **Never read the CLI description or version from a literal.**
  `argparse(description=__doc__.splitlines()[0])` crashes under `python -O`
  (`__doc__` is `None`), and a hardcoded version drifts from `pyproject.toml`.
  Read the version from the installed distribution; a test enforces agreement.
- **Guard the dispatcher's own arguments** — a tool name with no artifact, two
  targets beside a single-target flag.
- **CI must be pinned to the lock** (`uv sync --locked`), or CI silently drifts
  from what developers run.
- **A substring is not a directive.** `"#version" in src` matched a comment and
  dropped the shader's generated preamble. Anchor it (`^\s*#version`); the same
  goes for shebangs, `import`/`BEGIN` markers, and any sentinel.
- **Cross-check the maths, not only the graph.** The collision, clipping and
  coverage routines that decide verdicts get a reference library (Shapely) on
  random inputs — not a second copy of the same formula.
- **Pin the input language with a valid + invalid corpus.** The constructs an
  author will write must parse; malformed ones must be rejected. A false
  rejection is the tool lying about what it supports.
- **Keep strictness in the repo's config.** `strict = true` for mypy and the
  lint/format rules belong in `pyproject.toml`, not only in a CI command line, so
  the gate cannot quietly weaken; gate `ruff format --check` too.
- **Give the checker a memory (a baseline).** `--write-baseline` / `--baseline`
  record an accepted state and fail only on **new** errors; a checker that always
  fails on old debt gets switched off.
- **Cover every statement, and be explicit about the exceptions.** A 100% floor
  is the only one that stops new dark corners; `# pragma: no cover` only for a
  platform/version fallback. Delete a vestigial guard rather than cover it.
- **A gate must fail closed on an empty scope.** A reusable action that loops
  over `find … *.py` reports success when it finds nothing — a false green. Assert
  the zero-input case fails, and keep a test for it.
- **Move a runner's shell into a script.** Inline `run: |` cannot be linted or
  unit-tested; extract it to a checked-in script, `shellcheck` it, and drive it
  from the workflow and a test.
- **Scope a linter ignore inline, with a reason.** When a deliberate choice
  disagrees with a linter (local `uses: ./` vs zizmor's `$/`), annotate that one
  line (`# zizmor: ignore[rule] -- why`) instead of disabling the rule or drifting.
- **A runner's bash is not your bash.** `mapfile` does not exist in macOS's
  bash 3.2 (use a `while read` loop); Windows CI's `bash` is the WSL stub, so
  skip a shell test there and let the action use GitHub's `shell: bash`.
- **Pin the encoding on text I/O.** `read_text()` / `write_text()` default to the
  platform encoding (cp1252 on Windows); an exact-match test on a non-ASCII asset
  or a JSON file with `ensure_ascii=False` then fails only on Windows.
- **Guard drift across the whole tree.** A rename, a count or a release version
  lives in many docs. A test that scans every tracked
  `*.md`/`*.txt`/`*.yml`/`*.toml` for the canonical names and the release version
  (and checks the version has a CHANGELOG entry) catches a misspelled tool name
  in a publish loop and a `gxkit` where PyPI needs `gxkit-cli`.
- **A fix without a guard comes back.** Every defect leaves a permanent guard
  that has been *seen to fail* on the old state — a domain test, a whole-tree
  scan, a lint rule, or a CI leg on the platform where it broke. The
  `mistake-to-guard` skill is the procedure; `test_docs.py` is the whole-tree
  kind.
- **Assert layout invariants, not a golden image.** Determinism, non-overlap,
  on-canvas and "something was drawn" catch a layout drift that a screenshot
  baseline would bless.
- **Cross-check the reading, not only the primitive.** The tool that calls
  `reachable()`/`find_cycle()` must reach the same verdict as NetworkX on random
  models, and a *sound* random artifact must report zero problems.
- **Route on the real files, not fake classes, and hold a reported box against
  the drawn pixels** — both catch a defect that every unit check would pass.

## 7. What every tool ships

The loader **imports and runs** the artifact file — document this. A person
running `inspect` on an untrusted file is running a Python script. No tool in
this family makes network requests; say so, so the boundary is explicit.

`README.md`, `AGENTS.md`, `llms.txt` (one-file agent setup), `SKILL.md`; a
`uvx --from "<repo>#subdirectory=packages/<tool>" <tool> …` install path; and a
`payload = [(clean example), (every-fault example)]` under `examples/`.

**Adding a tool is a migration.** One bounded set (the packages and
`gxkit.registry.TOOLS`) is encoded by many consumers: the registry and the
codes, the generated architecture figure and `docs/TRACE.md`, the root
README/SKILL/llms/PLAN prose, `docs/LICENSING.md` (a new import joins a row), the
test maps that hardcode the set, the `gxkit` workspace sources, and the coverage
flags in `scripts/check.sh`/CI. Give every consumer map a test that it equals the
canonical set, then let the reds name the places you forgot — see the
`contract-shape-migration` skill.

**A figure, not decoration.** A README's first useful thing is one architecture
figure, generated deterministically from the code by a repo-owned script (no
hosted service, no CLI to install). Regenerate it and look at the rendered image
before committing — the same "look at the picture" rule as the storyboard.
Derive the figure's own labels (its title, `<desc>`, counts) from the list it
draws, and pin the committed asset to the generator with a test — a hardcoded
"nine" outlives the tenth tool when nothing checks.
(Producing it: `doc-figures`; front-page prose and scan order: `write-readme`;
hierarchy and restraint: `readme-visual-design`.)

For **real 3D or animation**, use a purpose-built engine, not a hand-rolled one —
gxkit's hero is a ManimGX scene (`docs/hero/gxkit_hero.py`), and the clip is
checked with `framegx`. Hand-rolling `mplot3d` or a raymarcher is the wrong axis:
gxkit's job is inspection, not rendering.

Pair it with **one concrete worked example** — a real catch with the command and
its output — so the reader sees value rather than a claim. A second figure earns
its place only if it carries distinct information; an image that only decorates
is clutter.

**One entry point, once there are several tools.** A `tools` list and an
`inspect <file>` that detects the artifact and routes to the right tool (the
routing table as code — see `packages/gxkit`). Name the tool explicitly as the
escape hatch, and accept a directory: run every artifact under it and fail if
any does.

**Expose the codes as data, ship a config, wire a CI gate.** A `codes` command
whose entries a test cross-checks against the source (so it cannot drift); a
`.gxkit.toml` so an adopter can silence a code without editing the tool; and a
reusable action that runs `inspect` as the gate — the exit code is the
integration point. See [`PLAN.md`](PLAN.md) and [`RELEASING.md`](RELEASING.md).

**A setup prompt, and an agent doc it can follow.** Two lines a person pastes
into Claude Code / Codex / Cursor, naming `llms.txt` and saying install-then-use;
the file must itself contain an explicit **Install** step or the chain breaks.

The license must travel with the package: declare an SPDX expression
(`license = "MIT"`) **and** a `LICENSE` file so the wheel carries it
(`license-files`); the deprecated free-text `License: MIT` ships no file.

## 8. Workflow

1. Name the artifact and the **objective property**; run the checklist.
2. Model the artifact as **data** (declarative: tables, edges, grids, boxes).
3. Write **checks** returning `Problem`s; reuse `gxcore.graph` / `layout`.
4. **Render** to a raster; map each problem's `target` to a `bbox`.
5. Wire `tool.py` with `scene_tool`.
6. Add **examples**: one that must pass, one with every fault injected.
7. Add **tests** that prove each check fires and stays quiet.
8. `inspect` the broken example; **look at the storyboard**; confirm the box
   numbers match the report.
9. Write `README` / `AGENTS` / `llms.txt` / `SKILL.md`.
10. Only now, if a second tool wants the same code, move it into `gxcore`.

## 9. Publishing

`scripts/prepublish_check.py` is the gate. It fails on credentials or machine
paths in tracked files (and on credentials anywhere in history), and prints the
commit authors, trailers and submodules. It runs in CI, and it was proven to
fail — on a real finding in this repository — before it was trusted. Run it
before any release or visibility change; the checklist behind it is the
`publish-readiness-audit` skill.

A release also wants: PyPI metadata (authors, keywords, classifiers, URLs), a
**dependency pin**, a type check if you ship `py.typed`, repository metadata
(description, topics, homepage), and dependency updates (Dependabot). See
[`RELEASING.md`](RELEASING.md).

CI must be strict enough to be worth trusting — least privilege (`permissions`,
`persist-credentials: false`), SHA-pinned actions, `concurrency` and timeouts, a
Python + one-non-Linux matrix, a coverage floor, a packaging job that also
installs the built sdist and smoke-tests the CLI, `zizmor` + `pip-audit`, and
Dependabot with a cooldown. The `publish-readiness-audit` skill has the
checklist.
