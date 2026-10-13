# protogx

**Inspect a protocol state machine for deadlocks, unhandled messages and
unreachable states.** Declare states, transitions and the messages that drive
them; `protogx inspect` proves every state is reachable, that "done" is reachable
from everywhere, and that no declared message or awaited response is left
unhandled.

One of the [`gxkit`](../../README.md) tools, built on [`gxcore`](../gxcore).

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/protogx" protogx inspect proto.py
# local:  uvx --from ../../packages/protogx protogx inspect proto.py
```

## Writing a protocol

```python
import protogx as p

protocol = p.Protocol(
    states=["closed", "listen", "syn_sent", "established", "closing"],
    start="closed",
    terminal=["closed"],
    messages=["SYN", "SYN+ACK", "ACK", "FIN"],
    transitions=[
        ("closed", "listen", None),          # internal
        ("listen", "syn_sent", "SYN"),
        ("syn_sent", "established", "SYN+ACK"),
        ("established", "closing", "FIN"),
        ("closing", "closed", "ACK"),
    ],
    requests=["SYN", "FIN"],
    responses={"SYN": "SYN+ACK", "FIN": "ACK"},
)
```

Or module-level `STATES` / `TRANSITIONS` / `START` / `TERMINAL` / `MESSAGES` /
`REQUESTS` / `RESPONSES`. Transitions are `(source, target)` or
`(source, target, message)`.

## The contract

```
$ protogx inspect broken_protocol.py
broken_protocol.py: Broken handshake
protocol: 5 states, 4 transitions
storyboard: Broken_handshake.storyboard.png
  5 states, 4 transitions
  5 messages, 1 requests
inspect: 8 problems (6 errors)
  [1] error established  nondeterministic: state 'established' handles 'ACK' 2 ways — ...
  [2] error -            missing-response: request 'SYN' expects 'SYN+ACK', which no transition handles
  [3] error -            unhandled-message: message 'FIN' is declared but no transition handles it
  ...
```

- **Exit code 1** when any `error`-severity problem is found.
- `--json` prints the same report machine-readably; `--no-storyboard` skips the
  image; `-o name.png` names it.

## Checks

| code | severity | what it means |
| --- | --- | --- |
| `no-start` | error | no start state (or it is not declared) |
| `unknown-state` | error | a transition names an undeclared state |
| `unknown-message` | error | a transition or response names an undeclared message |
| `unhandled-message` | error | a declared message no transition handles |
| `nondeterministic` | error | one state handles the same message two ways |
| `deadlock` | error | a reachable non-terminal state has no way out |
| `no-exit` | error | a reachable state can never reach a terminal state |
| `unreachable-state` | error | a state cannot be reached from the start |
| `no-terminal` | error | no terminal state, so the protocol can never end |
| `missing-response` | warn | a request's expected reply is never handled |
| `cycle` | info | a loop exists (often intentional) |

## Why it can be trusted

Every check is proven to fire on a protocol with the fault and to stay quiet on
one without (`tests/`). Deadlock, `no-exit` and cycles come from
`gxcore.graph`; the same analysis that finds soft-locks in a game level.

MIT licensed.
