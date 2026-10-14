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

### Write the model from the source of truth

An inspection that runs against a hand-copied model passes when the model goes stale. Generate
it from the artifact where you can - the environment variables the code reads, the imports, the
route table - and keep a `--check` mode that fails when the written model no longer matches what
the sources imply. Hand-write only what encodes a decision rather than a fact: a state machine,
a protocol, a network's intent. On `rust-browser-lab` this turned an `unused-variable` report
into three real bugs in one sitting - a launch that truncated the saved session, a trim policy
that could never fire, and a content-process entry point compiled out of the release build.

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

## Using a finding

The artifact is a description you wrote, so a finding is a claim about the description before it is a
claim about the thing. Check the artifact at the flagged place before repeating the finding as a
defect - the cost is one look, and the alternative is sending someone to fix something that is fine.

- **A red code usually means the description is wrong.** Four findings in one session across two
  tools were the model's fault: a protocol that "drops the connection on an unexpected packet"
  where the code says `continue`; a message "nothing handles" that has a dedicated wait; a state
  that "deadlocks" where a transition was simply not written down; five modules "unreachable"
  because the edge extraction only collected one spelling of a path.
- **Errors that survive that look are real and worth acting on.** A dependency cycle and two upward
  layer violations were read against the source and confirmed there.
- **`info` about dead code is usually about the model too.** "Nothing depends on this" often means
  the edges were missed, not that the code is unused.

## Write the artifact you want, not only the one you have

`inspect` answers "is this sound?". Pointing it at what you intend answers "can it be reached?", and
that is a gate you can put in CI before any work starts.

Keep both files and check them separately.

```
artifacts/
  machine.py          # as the code is today - may be broken, and the count must come down
  machine.target.py   # as you intend it - must report no problems, always
```

- **The target must be clean.** If a later change makes it report a violation, the intended design is
  no longer reachable and no code should move until that is understood.
- **The current one is allowed to be broken, but not to get worse.** Pin the error count and lower
  the limit as it falls, so progress is visible in the tool instead of asserted in a commit message.
- **A finding you intend to keep is still worth keeping.** A deliberate hole - an override flag that
  grants a low principal a sensitive permission - modelled and committed makes the risk precise and
  puts it next to the model that has none. Do not silence it; name it.

## What these tools do not check

They check the structure of a description, not the world. A foreign key from `chest.x` to
`world_cell.local_idx` is well-formed whether or not that row exists, so a schema check cannot see
the orphan - a container stored by position whose cell is absent from a sparse world. The same split
runs through all of them: a declared state nothing handles is a structural fault, a state handled in
a way nobody can observe is not.

For the part a checker cannot reach, write a test. **Structure can be an artifact and a gate;
existence has to be an assertion.**

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
| a random-seed manifest | `seedgx` | two streams that share a seed |
| a schedule of runs | `crongx` | two runs that hold a resource at once |

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
