# flowgx, for AI agents

A person pointed you here. `flowgx` checks that a state machine or flow chart can
actually finish: write the machine as data, then `flowgx inspect` proves every
state is reachable, every state can still reach "done", and no event is
ambiguous.

Part of `gxkit`; the review contract (`inspect`, `--json`, exit codes,
storyboard) is shared with every other tool in the family.

## Set it up

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/flowgx" flowgx --help
# or, from a clone:
uv tool install ./packages/flowgx
```

## Write a machine

A Python file with a `machine` (a `flowgx.Machine`), or `STATES` /
`TRANSITIONS` / `START` / `ACCEPT` lists:

```python
import flowgx as f

machine = f.Machine(
    states=["draft", "review", "published"],
    start="draft",
    accept=["published"],
    transitions=[
        ("draft", "review", "submit"),
        ("review", "published", "approve"),
    ],
)
```

## The loop

1. **Write** the machine as a `.py` file.
2. **Inspect** — `flowgx inspect machine.py`. It prints the states, accepting
   states, any cycle, and every problem with a stable `code`, and writes
   `<name>.storyboard.png`. **Exit 1 means at least one error.**
3. **Fix** and inspect again. View the storyboard: each numbered box marks a
   faulty state.
4. **Render** — `flowgx render machine.py -o machine.png`.

## Reading the report

- `error` — the flow is broken: a state nothing reaches (`unreachable-state`), a
  state that gets stuck (`dead-end`), a state that can never finish (`no-exit`),
  or one event that leads two ways (`ambiguous-transition`). Exit code 1.
- `info` — a cycle exists; keep it if the loop is intended.

The one that matters most is `no-exit`: a state you can reach but from which
"done" is impossible. That is the workflow form of a soft-lock.

`flowgx inspect checkout.mmd` reads a Mermaid state diagram instead of a
declaration — `[*] --> s` is the start, `s --> [*]` is accepting, `a --> b :
event` is a transition — and `flowgx inspect README.md` reads the one diagram a
document holds. The same codes apply, so a state drawn with an incoming edge
missing is `unreachable-state` exactly as it would be in a declaration. A
composite state, two initial states, or several diagrams in one document exits 2
with its line rather than a guess.
