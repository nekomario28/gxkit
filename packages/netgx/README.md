# netgx

**Inspect a network topology for segmentation and coherence faults.** Declare
nodes with a kind and the traffic allowed between them; `netgx inspect` finds an
edge to an unknown node, a public entry that reaches sensitive data, a self-loop,
a duplicate edge, an isolated node, and a topology with no public entry.

One of the [`gxkit`](../../README.md) tools, built on [`gxcore`](../gxcore)
(using its reachability and shortest-path checks).

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/netgx" netgx inspect net.py
# local:  uvx --from ../../packages/netgx netgx inspect net.py
```

## Writing a topology

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

## The contract

```
$ netgx inspect broken_network.py
broken_network.py: Flat network
network: 4 nodes, 5 edges
storyboard: Flat_network.storyboard.png
  4 nodes, 5 edges
inspect: 4 problems (2 errors)
  [1] error -          dangling-edge: edge web → ghost names unknown node 'ghost'
  [2] error db         public-reaches-sensitive: public 'internet' can reach sensitive 'db': internet → web → db
  [3] warn  legacy     self-loop: legacy allows traffic to itself
  [4] info  internet   duplicate-edge: edge internet → web is listed twice
```

- **Exit code 1** when any `error`-severity problem is found.
- `--json` prints the same report machine-readably; `--no-storyboard` skips the
  image; `-o name.png` names it.
- A baseline records findings by relationship. `dangling-edge` is identified by
  its edge and unknown endpoint, so pointing one edge at a different unknown
  node is a new error, not unchanged debt.

## Checks

| code | severity | what it means |
| --- | --- | --- |
| `dangling-edge` | error | an edge names an unknown node |
| `public-reaches-sensitive` | error | a public node can reach a sensitive one (path given); one finding per entry, identified by the route |
| `self-loop` | warn | a node allows traffic to itself |
| `duplicate-edge` | info | the same edge is listed twice |
| `isolated-node` | info | a node with no traffic in or out |
| `no-public` | info | no node is marked public |
| `no-nodes` | info | the network declares no nodes |

## Why it can be trusted

Every check is proven to fire on a topology with the fault and to stay quiet on
one without (`tests/`). Reachability and the shortest path come from
`gxcore.graph`; a public node reaching a sensitive one is the least-privilege
question.

MIT licensed.
