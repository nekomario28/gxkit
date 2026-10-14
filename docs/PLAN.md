# Plan — an agent-native review loop, and the tools built on it

Status: complete. All planned tools landed (P0–P8). This file is the durable
plan; keep it current if new tools are added.

How to add a tool (the checklist, the contract, the extraction rule) is in
[`BUILDING.md`](BUILDING.md).

## North star

Every creative artifact an agent makes should be **checkable before it ships**.
`manimgx inspect` proved the shape for animation: a domain-aware, machine-gated
review that reports *semantic* problems with stable codes, an exit code, and a
storyboard image as evidence. We are generalising that shape into a toolkit and
building it for the domains that do not have it yet.

The goal is not "a linter". It is **a review loop an agent can close on its
own**: write → inspect → fix → inspect → ship, with no human in the loop for
the mechanical part.

## Goals

Ordered; each is a checkpoint.

- **G0 — Shared core.** One library (`gxcore`) owns the review loop: the
  problem model, severities, exit policy, the storyboard annotator, the CLI,
  and the test convention. Domain tools only add domain knowledge.
- **G1 — Migrate the proof.** `chartgx` runs on `gxcore` with the same
  behaviour and the same tests green. No regression: the extraction earns its
  keep or it does not happen.
- **G2 — A second tool in an empty quadrant.** Something genuinely missing, not
  a clone of an existing linter. Candidates below; `levelgx` (game level
  design / playtest) chosen first because it is pure Python, needs no GPU, and
  the quadrant is empty.
- **G3 — Published.** `gxcore` and each tool installable on their own
  (`uvx --from … <tool>`), docs for agents (`llms.txt`, `AGENTS.md`,
  `SKILL.md`), CI green, tags + releases.
- **G4 — A directory.** A single place (`llms.txt` at the repo root) listing
  every tool, what it checks, and how to install it — so an agent can find the
  right reviewer for the artifact it just made.

## Shared components (`gxcore`)

The extraction is driven by what is *identical* across tools. Everything that
is not identical stays in the tool.

| component | responsibility | why shared |
| --- | --- | --- |
| `model.Problem` / `Report` | severity, stable `code`, `message`, `target`, located `bbox` | the contract every tool and every agent reads |
| severity + exit policy | `error` fails, `warn`/`info` do not | one rule, not one per tool |
| `geometry` | bbox overlap / area / edge-clipping | the same maths in every visual domain |
| `storyboard` | render a raster with numbered boxes over located problems | the "picture as evidence" contract |
| `report` | human text + `--json` | agents must not parse prose differently per tool |
| `cli` | `inspect` / `render`, `--json`, `--no-storyboard`, `-o`, exit codes, no tracebacks on a broken input | agent ergonomics for free |
| `testing` | "a check must be proven to fire, and to stay quiet" helpers | stops decorative checks across the family |
| `loading` | load an artifact from a Python file (attr → builder → fallback) | one discovery convention, not one per tool |
| `graph` | forward/reverse reachability, traps (soft-locks), cycles, components, terminals | `levelgx` walks a grid, `flowgx` walks a state machine — same questions |
| `layout` | text too small / clipped / overlapping, with messages | `chartgx` and `flowgx` label pixels the same way |
| `diagram` | a deterministic circular node-link renderer (circles + arrows + labels) | `flowgx`, `authzgx`, `depsgx` draw once |
| `toolkit` | build a raster tool's `Tool` + `main` from `load`/`inspect`/`to_image` | four tools' `tool.py` became five lines each |

## Efficiency model

The marginal cost of the **n-th tool** is the design goal. With `gxcore`:

```
new tool = 1 loader        (file -> artifact)
         + 1 checks module (artifact -> [Problem])
         + 1 renderer      (artifact -> raster/PNG)
```

Everything else — CLI, JSON, exit codes, storyboard, test harness, skill,
`llms.txt`, CI, and now the graph and layout analysis — is inherited. Measured
so far: `gxcore` was unchanged when `flowgx` was added; `flowgx` reuses
`gxcore.graph` for the same soft-lock question `levelgx` asks, and
`gxcore.layout` for label checks `chartgx` already had.

Secondary efficiencies:

- **One repo, one CI, one workspace** (`uv` workspace). Cross-tool fixes land
  once.
- **One storyboard annotator.** A tool author never writes image code.
- **One report format.** An agent that understands `chartgx --json` understands
  every future tool.
- **Tests are near-free**: a check is one figure/level/machine plus one assertion.

## Roadmap

Ranked by (gap strength × feasibility). From `docs/agent-native-landscape.md`.

- **P0 — `gxcore` + migrate `chartgx`.** *done*
- **P1 — `levelgx`.** Game / level design with an automated playtest. *done*
- **P2 — extract `graph` / `loading` / `layout`; add `flowgx`.** The second and
  third tools revealed the shared analysis; `flowgx` proves it (a state machine
  is the workflow form of the same soft-lock). *done*
- **P2.5 — extract `diagram`; add `authzgx`.** The graph renderer moved to
  `gxcore.diagram`; `authzgx` answers "can a low principal reach a sensitive
  permission?" with `gxcore.graph.shortest_path`. *done*
- **P2.6 — extract `toolkit`; add `depsgx`.** The tool scaffolding moved to
  `gxcore.toolkit` (a tool's `tool.py` is now `scene_tool(...)`); `depsgx`
  inspects module dependency graphs for cycles, layer violations and dead code.
  Two storyboard bugs were found by looking at the pictures (a flipped origin
  and mismatched numbering) and fixed in the core. *done*
- **P2.7 — `schemagx`.** Relational schemas: dangling foreign keys, type
  mismatches, foreign-key cycles (excluding self-references, which are trees)
  and dead tables. *done*
- **P3 — `docgx`.** Pages / slides: text overflow, overlap, tiny text, word
  budget, reading order. The second real consumer of `gxcore.layout` (after
  `chartgx`), which also exposed that the overlap metric ignored a small box
  nested inside a large one. *done*
- **P3.5 — `protogx`.** Protocol state machines: deadlocks, unreachable states,
  and the message-level checks a plain state machine cannot see — a declared
  message nothing handles, a request whose reply never arrives. *done*
- **P4 — `shadergx`.** Fragment shaders rendered headlessly through moderngl +
  EGL: compile errors, a black / constant / NaN frame, and — because an agent
  cannot see the pixels — a uniform that is set but never reaches the output
  (grounded in the GLSL compiler removing unused uniforms). Tests skip where no
  GL context exists. *done*
- **P5 — `framegx`, and pair with ManimGX.** The rendered *file*: black, frozen,
  wrong length, missing or silent sound — the failures a scene-level inspector
  cannot see. ManimGX makes the animation and checks the scene; `framegx` checks
  the encoded result, so `manimgx render scene.py && framegx inspect clip.py`
  closes the loop. Uses ffmpeg. *done*
- **P6 — `gxkit`, the umbrella.** One entry point: `gxkit inspect <file>`
  detects the artifact's tool and runs it, `gxkit tools` lists the catalogue. The
  family skill's routing promise, made executable. *done*
- **P7 — distribution and operation.** `gxkit codes` (a machine-readable
  catalogue, cross-checked against the source), `.gxkit.toml` config (ignore a
  code, change a severity), a reusable GitHub Action, and release tooling
  (`uv build` + `twine check`; see [`RELEASING.md`](RELEASING.md)). The umbrella
  publishes as **`gxkit-cli`** — `gxkit` is taken on PyPI. *done*
- **P8 — publish.** The repository is public with tags, releases and an action;
  PyPI/npm names are claimed (all free except `gxkit`).

- **P9 — `apigx`.** HTTP API contracts: duplicate routes, a state-changing
  method with no authentication, a path outside the versioned base. Added after
  the ten-tool snapshot. *done*

- **P10 — `netgx`.** Network topologies: an edge to an unknown node, a public
  entry that reaches sensitive data, a self-loop. The least-privilege question,
  on the same reachability core. *done*

- **P11 — `envgx`.** Environment / config drift: an undeclared reference, a
  secret with a default, an unknown type, an unused declaration. *done*

## Definition of done

- `gxcore`: model, geometry, storyboard, report, cli, testing, loading, graph,
  layout — each with tests.
- Every tool: `inspect` exits non-zero on error, writes a storyboard, prints
  `--json`, and has a test that proves each check can fail.
- CI runs `uv sync --all-packages && uv run pytest` on push.
- Each tool ships `README.md`, `AGENTS.md`, `llms.txt`, `SKILL.md`.
- `uvx --from <git-url>#subdirectory=packages/<tool> <tool> --help` works from a
  clean cache.

## Naming

Working names; confirm availability on PyPI/npm before publishing.

- repo: **`gxkit`**
- core: **`gxcore`**
- tools keep a `*gx` suffix: `chartgx`, `levelgx`, `shadergx`, `docgx`.

## Layout

```
gxkit/
  packages/
    gxcore/     the shared review loop
    chartgx/    matplotlib charts
    levelgx/    game levels (playtest)
  docs/         this plan, the landscape research
  .github/      CI
```
