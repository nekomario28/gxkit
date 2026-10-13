# Plan — an agent-native review loop, and the tools built on it

Status: P0 in progress. This file is the durable plan; update it as phases land.

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

## Efficiency model

The marginal cost of the **n-th tool** is the design goal. With `gxcore`:

```
new tool = 1 loader        (file -> artifact)
         + 1 checks module (artifact -> [Problem])
         + 1 renderer      (artifact -> raster/PNG)
```

Everything else — CLI, JSON, exit codes, storyboard, test harness, skill,
`llms.txt`, CI — is inherited. That is the whole point of the extraction.

Secondary efficiencies:

- **One repo, one CI, one workspace** (`uv` workspace). Cross-tool fixes land
  once.
- **One storyboard annotator.** A tool author never writes image code.
- **One report format.** An agent that understands `chartgx --json` understands
  every future tool.
- **Tests are near-free**: a check is one figure/level plus one assertion.

## Roadmap

Ranked by (gap strength × feasibility). From `docs/agent-native-landscape.md`.

- **P0 — `gxcore` + migrate `chartgx`.** *this phase*
- **P1 — `levelgx`.** Game / level design with an automated playtest: build a
  grid level in Python, then flood-fill the reachable set and prove the goal is
  solvable, no collectible is stranded, and no soft-lock exists. Pure Python,
  no GPU. Empty quadrant. *this phase*
- **P2 — `shadergx`.** Shader / GPU graphics: render a fixed test pattern,
  inspect for all-black / NaN (via float target), constant output, and expected
  vs actual coverage. Needs a headless GL stack; budget for it.
- **P3 — `docgx`.** Document / slide layout: build HTML or Typst, render, then
  reuse the exact text-overlap / clipping / overflow checks from `chartgx`.
  Mostly a new loader — the checks already exist.
- **P4 — publish.** Names checked on PyPI/npm, core released, tools released,
  root `llms.txt` directory.

## Definition of done

- `gxcore`: model, geometry, storyboard, report, cli, testing — each with tests.
- Every tool: `inspect` exits non-zero on error, writes a storyboard, prints
  `--json`, and has a test that proves each check can fail.
- CI runs `uv sync --all-packages && uv run pytest` on push.
- Each tool ships `README.md`, `AGENTS.md`, `llms.txt`, `SKILL.md`.
- `uvx --from <repo>@<tool-subdir> <tool> --help` works from a clean cache.

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
