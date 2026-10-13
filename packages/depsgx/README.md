# depsgx

**Inspect a module dependency graph for cycles, layer violations and dead
code.** Declare modules and what they depend on; `depsgx inspect` proves the
graph is acyclic, that no dependency points *upward* through the layers, and
that nothing is unreachable from the entry points — then draws the graph with
the faulty modules boxed.

One of the [`gxkit`](../../README.md) tools, built on [`gxcore`](../gxcore).

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/depsgx" depsgx inspect deps.py
# local:  uvx --from ../../packages/depsgx depsgx inspect deps.py
```

## Writing a graph

```python
import depsgx as d

graph = d.ModuleGraph(
    modules=["api", "service", "domain", "util"],
    depends=[("api", "service"), ("service", "domain"), ("domain", "util")],
    roots=["api"],                                        # entry points
    layers=[["api"], ["service"], ["domain"], ["util"]],  # top -> bottom
    forbidden=[("domain", "infra")],                      # explicit bans
)
```

Or module-level `MODULES` / `DEPENDS` / `ROOTS` / `FORBIDDEN` / `LAYERS`.

`depends` edges point from a module to what it imports. Anything not reachable
from the roots is dead code. With `layers`, a dependency that points upward (a
lower layer importing a higher one) is a layer violation.

## The contract

```
$ depsgx inspect broken_modules.py
broken_modules.py: Tangle
modules: 6 modules, 7 dependencies
storyboard: Tangle.storyboard.png
  6 modules, 7 dependencies
  roots: api
  layers (top→bottom): api | service | domain | infra | util
inspect: 7 problems (5 errors)
  [1] error api     cycle: dependency cycle: api → service → domain → util → api
  [2] error domain  forbidden-dependency: 'domain' must not depend on 'infra'
  [3] error legacy  self-dependency: module 'legacy' depends on itself
  [4] error util    layer-violation: 'util' (layer 4) depends on 'api' (layer 0) — ...
  [5] error util    dangling-dependency: dependency names unknown module 'ghost'
  ...
```

- **Exit code 1** when any `error`-severity problem is found.
- `--json` prints the same report machine-readably; `--no-storyboard` skips the
  image; `-o name.png` names it.

## Checks

| code | severity | what it means |
| --- | --- | --- |
| `cycle` | error | the dependency graph has a cycle |
| `layer-violation` | error | a lower layer depends on a higher one |
| `forbidden-dependency` | error | an explicitly banned dependency exists |
| `self-dependency` | error | a module depends on itself |
| `dangling-dependency` | error | a dependency names an undeclared module |
| `unreachable-module` | info | not reachable from any root — dead code |
| `orphan-module` | info | nothing depends on it and it is not a root |
| `duplicate-dependency` | info | the same edge is listed more than once |
| `no-roots` | info | no entry points, so dead code cannot be found |

## Why it can be trusted

Every check is proven to fire on a graph with the fault and to stay quiet on one
without (`tests/`). Cycles come from `gxcore.graph.find_cycle` and dead code
from reachability out of the roots — the same graph analysis that finds
soft-locks in a game level.

MIT licensed.
