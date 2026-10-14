# flowgx

**Inspect state machines and flow charts for structural faults.** Declare a
machine as data; `flowgx inspect` proves every state is reachable, every state
can still reach "done", and no event is ambiguous — then draws a storyboard with
the faulty states boxed.

One of the [`gxkit`](../../README.md) tools, built on [`gxcore`](../gxcore).

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/flowgx" flowgx inspect machine.py
# local:  uvx --from ../../packages/flowgx flowgx inspect machine.py
```

## Writing a machine

```python
import flowgx as f

machine = f.Machine(
    states=["draft", "review", "changes", "published", "archived"],
    start="draft",
    accept=["published", "archived"],
    transitions=[
        ("draft", "review", "submit"),
        ("review", "published", "approve"),
        ("review", "changes", "request"),
        ("changes", "review", "resubmit"),
        ("published", "archived", "archive"),
    ],
)
```

Or module-level `STATES` / `TRANSITIONS` / `START` / `ACCEPT` lists. Transitions
are `(source, target)` or `(source, target, event)`. With no `accept`, states
that have no outgoing transition are treated as accepting.

## The contract

```
$ flowgx inspect broken_machine.py
broken_machine.py: Broken review workflow
machine: 6 states
storyboard: Broken_review_workflow.storyboard.png
  6 states, 5 transitions
  accepting: published
inspect: 4 problems (4 errors)
  [1] error changes    no-exit: state 'changes' cannot reach any accepting state — the flow can never complete from here
  [2] error limbo      dead-end: state 'limbo' has no outgoing transition and is not accepting — the flow gets stuck
  [3] error rejected   unreachable-state: state 'rejected' cannot be reached from 'draft'
  [4] error review     ambiguous-transition: state 'review' has more than one 'act' transition — the flow is non-deterministic
```

- **Exit code 1** when any `error`-severity problem is found.
- `--json` prints the same report machine-readably; `--no-storyboard` skips the
  image; `-o name.png` names it.

## Checks

| code | severity | what it means |
| --- | --- | --- |
| `no-start` | error | no start state (or it is not declared) |
| `no-accept` | error | no accepting/terminal state, so "done" is undefined |
| `unknown-state` | error | a transition names a state that was not declared |
| `unreachable-state` | error | a state cannot be reached from the start |
| `dead-end` | error | a reachable state has no way out and is not accepting |
| `no-exit` | error | a reachable state can never reach an accepting state |
| `ambiguous-transition` | error | two transitions from one state share an event |
| `cycle` | info | a loop exists (often intentional) |

`no-exit` is the workflow form of a soft-lock: `gxcore.graph` computes the states
that are reachable but from which the goal is not.

## Why it can be trusted

Every check is proven to fire on a machine with the fault and to stay quiet on
one without (`tests/`), including the shared text-layout checks reused from
`gxcore`.

MIT licensed.
