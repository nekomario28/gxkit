# Building a `*gx` tool

Build the loop an agent can close on its own:

```
write artifact as code  →  inspect (codes + exit code + storyboard)  →  fix  →  inspect  →  ship
```

The reference implementation is **gxkit** at `gxkit`
(`gxcore` + `chartgx`, `levelgx`, `flowgx`, `authzgx`, `depsgx`, `schemagx`, `docgx`).
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

Use `gxcore.testing` (`assert_fires`, `assert_quiet`, `has`, `codes`). Inject
the defect into a real artifact (a figure, a level, a machine), not a mock.

## 5. Two disciplines that caught real bugs

- **Look at the storyboard image.** Every rendering bug in this project — a
  vertically flipped origin, a numbering that disagreed with the report,
  co-located problems whose boxes hid each other — was invisible in the text
  report and obvious in the picture. When you can view images, view them.
- **Measure exit codes correctly.** `tool … | tail; echo $?` prints `tail`'s
  code, not the tool's. Capture `$?` immediately after the tool runs.

## 6. Pitfalls learned from the family

- **Nested boxes.** "Do these two collide?" must ask whether the *smaller* box
  is mostly inside the other. Requiring *both* to be covered misses a small
  label sitting on a large block.
- **Legitimate self-loops.** A self-referential edge (a `manager_id` tree, a
  retry loop) is not a cycle. Exclude self-edges before `find_cycle`, or you
  report trees as faults *and* hide the real cycle behind them.
- **Stale core wheel.** In a multi-package workspace, installing one tool reuses
  a cached wheel of the shared core. When the core changes, bump its version, or
  the tool fails at import (`ModuleNotFoundError: gxcore.toolkit`).

## 7. What every tool ships

`README.md`, `AGENTS.md`, `llms.txt` (one-file agent setup), `SKILL.md`; a
`uvx --from "<repo>#subdirectory=packages/<tool>" <tool> …` install path; and a
`payload = [(clean example), (every-fault example)]` under `examples/`.

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
