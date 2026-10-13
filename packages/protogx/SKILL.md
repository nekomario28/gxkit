---
name: protogx
description: Inspect a protocol / message state machine before implementing it — a state nothing reaches, a state that deadlocks, a state from which no terminal state is reachable, a declared message nothing handles, a request whose expected reply never arrives, or two transitions on the same message in one state. Declare states, transitions, messages and requests/responses as data; get stable codes, exit codes, and an annotated storyboard. Use when designing or generating a network protocol, handshake, RPC/command lifecycle, connection state machine, or message-driven flow and you need to prove it can progress and finish — especially when an agent wrote it. Not for verifying a real implementation against a spec, or for arbitrary code.
---

# protogx — prove a protocol can progress and finish

Part of the `gxkit` family; the review contract is shared with every `*gx` tool.

## Install

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/protogx" protogx --help
uv tool install ./packages/protogx
```

## Write a protocol

```python
import protogx as p

protocol = p.Protocol(
    states=["closed", "listen", "established", "closing"],
    start="closed",
    terminal=["closed"],
    messages=["SYN", "ACK", "FIN"],
    transitions=[
        ("closed", "listen", None),
        ("listen", "established", "SYN"),
        ("established", "closing", "FIN"),
        ("closing", "closed", "ACK"),
    ],
    requests=["SYN", "FIN"],
    responses={"SYN": "ACK", "FIN": "ACK"},
)
```

Or module-level `STATES` / `TRANSITIONS` / `START` / `TERMINAL` / `MESSAGES` /
`REQUESTS` / `RESPONSES`. Transitions are `(source, target)` or
`(source, target, message)`.

## The loop

1. Write the protocol as a Python file.
2. `protogx inspect proto.py` — states, transitions, problems with stable
   `code`s, and `<name>.storyboard.png`. **Exit 1 on any error.**
3. Fix and inspect again; the storyboard boxes each faulty state.
4. `protogx render proto.py -o proto.png`.

## Severities

`error` = the protocol is broken. `warn` = a request whose reply is never
handled. `info` = a loop exists (keep it if intended).

## What it catches

| code | severity | meaning |
| --- | --- | --- |
| `no-start` | error | no start state |
| `unknown-state` | error | a transition names an undeclared state |
| `unknown-message` | error | a transition or response names an undeclared message |
| `unhandled-message` | error | a declared message no transition handles |
| `nondeterministic` | error | one state handles the same message two ways |
| `deadlock` | error | a reachable non-terminal state has no way out |
| `no-exit` | error | a reachable state can never reach a terminal state |
| `unreachable-state` | error | a state cannot be reached from the start |
| `no-terminal` | error | no terminal state, so it can never end |
| `missing-response` | warn | a request's expected reply is never handled |
| `cycle` | info | a loop exists |

`unhandled-message` and `missing-response` are what a plain state-machine check
cannot see: they are about *messages*, not states. Everything else is
`gxcore.graph` reachability. Every check has a test that proves it fires on a
protocol with the fault and stays quiet on one without (`tests/`).
