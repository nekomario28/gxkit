---
name: depsgx
description: Inspect a module / package dependency graph for architectural faults before they spread — dependency cycles, layer violations (a lower layer importing a higher one), banned dependencies, self-dependencies, dangling references, and dead code unreachable from the entry points. Declare modules, edges, roots and layers as data; get stable codes, exit codes, and an annotated storyboard. Use when designing or generating a module layout, package structure, service dependency map, or build graph and you need to prove it stays acyclic and layered — especially when an agent is writing the structure. Not for scanning a specific language's real imports (use its linter) or for runtime dependency resolution.
---

# depsgx — prove a dependency graph is acyclic and layered

Part of the `gxkit` family; the review contract is shared with every `*gx` tool.

## Install

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/depsgx" depsgx --help
uv tool install ./packages/depsgx
```

## Write a graph

```python
import depsgx as d

graph = d.ModuleGraph(
    modules=["api", "service", "domain", "util"],
    depends=[("api", "service"), ("service", "domain"), ("domain", "util")],
    roots=["api"],
    layers=[["api"], ["service"], ["domain"], ["util"]],
    forbidden=[("domain", "infra")],
)
```

Or module-level `MODULES` / `DEPENDS` / `ROOTS` / `FORBIDDEN` / `LAYERS`.

## The loop

1. Write the graph as a Python file.
2. `depsgx inspect deps.py` — modules, roots, layers, problems with stable
   `code`s, and `<name>.storyboard.png`. **Exit 1 on any error.**
3. Fix and inspect again; the storyboard boxes each faulty module.
4. `depsgx render deps.py -o deps.png`.

## Severities

`error` = the architecture is broken. `info` = dead code or configuration notes.

## What it catches

| code | severity | meaning |
| --- | --- | --- |
| `cycle` | error | the graph has a cycle |
| `layer-violation` | error | a lower layer depends on a higher one |
| `forbidden-dependency` | error | an explicitly banned dependency exists |
| `self-dependency` | error | a module depends on itself |
| `dangling-dependency` | error | a dependency names an undeclared module |
| `dangling-reference` | error | `forbidden`/`layers`/`roots` names no module |
| `unreachable-module` | info | not reachable from any root — dead code |
| `orphan-module` | info | nothing depends on it and it is not a root |
| `duplicate-dependency` | info | the same edge is listed twice |
| `no-roots` | info | no entry points, so dead code cannot be found |

Cycles come from `gxcore.graph.find_cycle` and dead code from reachability out
of the roots. Every check has a test that proves it fires on a graph with the
fault and stays quiet on one without (`tests/`).
