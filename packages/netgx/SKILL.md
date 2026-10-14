---
name: netgx
description: Use when an agent has written a network topology (nodes with a kind plus the allowed traffic) and must check it before building — an edge to an unknown node, a public entry that reaches sensitive data, a self-loop, a duplicate edge, an isolated node, or no public entry. Provides `netgx inspect` with stable codes, an exit code, `--json` and a storyboard. Part of the gxkit family.
---

# netgx

`netgx` reads a network topology written as data and reports what is wrong before
anyone builds it — with the least-privilege question (can public reach sensitive
data?) at its centre.

## Use it

```sh
uv tool install "git+https://github.com/nekomario28/gxkit#subdirectory=packages/netgx"
netgx inspect net.py            # report + storyboard; exit 1 on any error
netgx inspect net.py --json
netgx render  net.py -o net.png
```

Write the topology as a Python file:

```python
import netgx as n

net = n.Network(
    nodes={"internet": "public", "web": "service", "db": "data"},
    edges=[("internet", "web")],
    sensitive=["db"],
)
```

A node kind is `public`, `edge`, `service` or `data`. Or module-level `NODES` /
`EDGES` / `SENSITIVE`.

## What it catches

| code | severity | what it means |
| --- | --- | --- |
| `dangling-edge` | error | an edge names an unknown node |
| `public-reaches-sensitive` | error | a public node can reach a sensitive one (path given) |
| `self-loop` | warn | a node allows traffic to itself |
| `duplicate-edge` | info | the same edge is listed twice |
| `isolated-node` | info | a node with no traffic in or out |
| `no-public` | info | no node is marked public |

## Why the checks can be trusted

Every check has a test that builds the defect and asserts it fires, and one that
asserts an honest topology stays quiet (`packages/netgx/tests/`). Reachability and
the shortest path come from `gxcore.graph`.

## Where it fits

Part of `gxkit`; the `inspect` contract (stable codes, exit codes, `--json`, a
storyboard) is shared. See the family skill at the repository root.
