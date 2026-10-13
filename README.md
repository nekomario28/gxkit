# gxkit

**Agent-native review loops for creative artifacts.** Give an agent a tool that
can check its own work: write the artifact as code, `inspect` it, get problems
with stable codes and an exit code, fix them, and ship — with a storyboard image
as the evidence.

`gxkit` is the shared engine plus the tools built on it. Each tool owns one
domain; the review loop is written once.

| tool | checks | status |
| --- | --- | --- |
| **`chartgx`** | matplotlib charts: truncated baselines, clipped/overlapping text, missing titles/labels/units, dual axes, unreadable pies, constant or clipped data | working |
| **`levelgx`** | game levels: reachability, solvability, stranded collectibles, no-exit and soft-lock | working |
| **`flowgx`** | state machines / flow charts: unreachable states, dead ends, states that can never finish, non-deterministic events | working |
| **`authzgx`** | permission models: privilege-escalation paths, inheritance cycles, dangling references, dead config | working |
| **`depsgx`** | module dependency graphs: cycles, layer violations, banned edges, dead code | working |
| **`schemagx`** | relational schemas: dangling keys, type mismatches, foreign-key cycles, dead tables | working |
| **`docgx`** | pages / slides: text that overflows the canvas, blocks that overlap, tiny text, out-of-order blocks | working |
| **`protogx`** | protocol state machines: deadlocks, unhandled messages, missing responses, unreachable states | working |
| **`shadergx`** | fragment shaders: compile errors, black / constant / NaN output, unused uniforms | working |

## The loop

Every tool has the same contract:

```sh
<tool> inspect artifact.py     # problems + storyboard, exit 1 on any error
<tool> inspect artifact.py --json
<tool> render  artifact.py -o out.png
```

- **Exit code 1** when any `error`-severity problem is found. `warn` and `info`
  never fail the build.
- **A storyboard image** with each located problem boxed and numbered, so the
  text report and the picture agree.
- **Stable codes** (`truncated-baseline`, `stranded-item`, …) an agent branches
  on, never on prose.

## Why a family, not a tool

The expensive part of a review loop is not the checks — it is the contract:
severities, exit codes, the storyboard, the JSON, the CLI, the test convention.
`gxcore` owns all of it, plus the analysis the tools share:

- **`gxcore.model` / `cli` / `storyboard` / `report`** — the loop itself.
- **`gxcore.graph`** — directed reachability, reverse reachability, traps
  (soft-locks), cycles, components. Used by `levelgx` *and* `flowgx`.
- **`gxcore.layout`** — text too small / clipped / overlapping. Used by
  `chartgx` *and* `flowgx`.
- **`gxcore.loading`** — load an artifact from a Python file, one convention.
- **`gxcore.diagram`** — a deterministic node-link renderer (circles + arrows).
  Used by `flowgx`, `authzgx` and `depsgx`.
- **`gxcore.toolkit`** — build a raster tool's `Tool`/`main` from three
  callables, so a tool's `tool.py` is five lines.

A new tool is three things:

```
loader        file -> artifact
checks        artifact -> [Problem]
renderer      artifact -> PNG
```

…and inherits the rest. See [`docs/BUILDING.md`](docs/BUILDING.md) for how to
add a tool (the checklist, the contract, the extraction rule),
[`docs/PLAN.md`](docs/PLAN.md) for goals, the efficiency model, and the
roadmap, and [`docs/agent-native-landscape.md`](docs/agent-native-landscape.md)
for which domains are still empty.

## Layout

```
packages/
  gxcore/     the shared review loop + graph / layout / loading / diagram
  chartgx/    matplotlib charts
  levelgx/    game levels
  flowgx/     state machines / flow charts
  authzgx/    permission models / RBAC
  depsgx/     module dependency graphs
  schemagx/   relational schemas
  docgx/      pages / slides
  protogx/    protocol state machines
  shadergx/   fragment shaders (GPU)
docs/
```

## Develop

```sh
uv sync --all-packages
uv run pytest
uv run chartgx inspect packages/chartgx/examples/bad_chart.py       # exit 1
uv run levelgx inspect packages/levelgx/examples/softlock_level.py # exit 1
uv run flowgx  inspect packages/flowgx/examples/broken_machine.py  # exit 1
uv run authzgx inspect packages/authzgx/examples/escalate_auth.py  # exit 1
uv run depsgx  inspect packages/depsgx/examples/broken_modules.py   # exit 1
uv run schemagx inspect packages/schemagx/examples/broken_schema.py  # exit 1
uv run docgx   inspect packages/docgx/examples/crowded_page.py      # exit 1
uv run protogx inspect packages/protogx/examples/broken_protocol.py  # exit 1
uv run shadergx inspect packages/shadergx/examples/broken_shader.py  # exit 1
```

## Use a tool on its own

```sh
uvx --from ./packages/chartgx chartgx inspect chart.py
uvx --from ./packages/levelgx levelgx inspect level.py
uvx --from ./packages/flowgx  flowgx  inspect machine.py
# or from GitHub:
# uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/chartgx" chartgx inspect chart.py
```

## Security

`inspect` reads the artifact by **importing and running the Python file** you
give it (that is how it gets a `fig`, a `level`, a `machine`, …). Only run
`<tool> inspect` on files you trust — the same rule as running any Python
script. `shadergx` additionally compiles and runs GLSL on your GPU. No tool
makes network requests.

Before publishing, `python scripts/prepublish_check.py` fails on credentials or
machine paths in the working tree (and on credentials anywhere in history).

MIT licensed. Every package declares `License-Expression: MIT` (SPDX) and ships
its `LICENSE` in the wheel. The reasoning (and why not Apache-2.0) is in
[`docs/LICENSING.md`](docs/LICENSING.md).

The `inspect` pattern is a generalisation of ManimGX's `inspect` command; see
the acknowledgements in that file.
