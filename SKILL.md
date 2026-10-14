---
name: gxkit
description: Use when an artifact an agent produced must be checked before it ships — a matplotlib chart, a game level, a state machine, a protocol, a permission/RBAC model, a module dependency graph, a relational schema, a page/slide, or a fragment shader — or when working inside the gxkit repository. Provides the shared `inspect` contract (stable problem codes, severities, an exit code, and a storyboard image) and routes to the one tool per domain. Not for making the artifact (that is a renderer/animation tool) nor for general code style (use the language linter).
---

# gxkit

**Agent-native review loops for creative artifacts.** Write the artifact as code,
`inspect` it, fix the problems, and ship — with a storyboard image as evidence.
The point is a loop an agent can close **on its own**: it cannot see its own
output, so the tool renders it, reads the pixels, and reports problems as codes.

## Start here

```sh
gxkit inspect artifact.py     # detect the artifact and route to its tool
gxkit tools                   # list what can be inspected
gxkit codes                   # every problem code and its severity
```

Or name the tool: `gxkit inspect levelgx level.py`. A `.gxkit.toml` up the tree
can ignore a code or change its severity; `--no-config` skips it.

## The contract (every tool, identical)

```sh
<tool> inspect artifact.py     # report + storyboard; exit 1 on any error
<tool> inspect artifact.py --json
<tool> render  artifact.py -o out.png
```

- **Exit 1** on any `error`; `warn` and `info` never fail.
- **Stable codes** (`truncated-baseline`, `soft-lock`, `escalation`, …) — branch
  on the code, never on prose.
- **A storyboard image** with each located problem boxed and numbered, matching
  the text report.
- **A baseline** (`--baseline` / `--write-baseline`) records an accepted state so
  a re-run reports new / fixed / unchanged and fails only on **new** errors.
  Commit the `.gxkit-baseline.json` it writes.

## Route to the tool

| artifact written as… | tool | it catches (the headline) |
| --- | --- | --- |
| matplotlib figure | `chartgx` | a bar chart whose baseline is not zero |
| level grid (`rows`) | `levelgx` | a soft-lock from a one-way tile |
| `Machine(states, transitions)` | `flowgx` | a state that can never reach "done" |
| `Protocol(...)` with messages | `protogx` | a declared message nothing handles |
| `AuthModel(roles, grants)` | `authzgx` | a low principal reaching a sensitive permission |
| `ModuleGraph(depends, layers)` | `depsgx` | a lower layer importing a higher one |
| `Schema(tables, foreign_keys)` | `schemagx` | a foreign-key cycle |
| `Page(title, blocks)` | `docgx` | text that overflows the canvas |
| GLSL fragment shader | `shadergx` | a uniform that never reaches the output |
| a rendered animation | `framegx` | a frozen or black render |
| an HTTP API contract | `apigx` | a mutating route with no authentication |
| a network topology | `netgx` | a public entry that reaches sensitive data |
| an environment / config | `envgx` | a secret that carries a default |
| a build pipeline | `pipegx` | a `needs` that names no step |

Each tool has its own `SKILL.md` under `packages/<tool>/SKILL.md` with the exact
input format, checks and codes. Read the one matching the artifact.

## Run it

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/<tool>" <tool> inspect artifact.py
# or, in a clone:  uv run <tool> inspect artifact.py
```

`chartgx` also needs matplotlib; `shadergx` needs a GL context.

## Working on gxkit itself

- The shared core is `packages/gxcore` (the review loop + `graph`, `layout`,
  `diagram`, `loading`, `toolkit`). A new tool is a loader, a checks module and
  a renderer; its `tool.py` is five lines.
- Adding a tool: [`docs/BUILDING.md`](docs/BUILDING.md) and the
  `agent-native-inspect-tools` skill.
- README and figures: the `write-readme` and `doc-figures` skills.
- Before publishing: `python scripts/prepublish_check.py`.

## Security

`inspect` reads the artifact by importing and running the Python file, so only
run it on files you trust. No tool makes network requests.
