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
| `shadergx` | shader / GPU output | planned |
| `docgx` | document / slide layout | planned |

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

A new tool is three things:

```
loader        file -> artifact
checks        artifact -> [Problem]
renderer      artifact -> PNG
```

…and inherits the rest. See [`docs/PLAN.md`](docs/PLAN.md) for goals, the
efficiency model, and the roadmap; [`docs/agent-native-landscape.md`](docs/agent-native-landscape.md)
for which domains are still empty.

## Layout

```
packages/
  gxcore/     the shared review loop + graph / layout / loading / diagram
  chartgx/    matplotlib charts
  levelgx/    game levels
  flowgx/     state machines / flow charts
  authzgx/    permission models / RBAC
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
```

## Use a tool on its own

```sh
uvx --from ./packages/chartgx chartgx inspect chart.py
uvx --from ./packages/levelgx levelgx inspect level.py
uvx --from ./packages/flowgx  flowgx  inspect machine.py
# or from GitHub:
# uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/chartgx" chartgx inspect chart.py
```

MIT licensed.
