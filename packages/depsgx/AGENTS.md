# depsgx, for AI agents

A person pointed you here. `depsgx` checks a module dependency graph for
architectural faults before they spread: declare modules and what they depend
on, then `depsgx inspect` proves the graph is acyclic, that nothing imports
upward through the layers, and that nothing is dead code.

Part of `gxkit`; the review contract (`inspect`, `--json`, exit codes,
storyboard) is shared with every other tool in the family.

## Set it up

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
)
```

Or module-level `MODULES` / `DEPENDS` / `ROOTS` / `FORBIDDEN` / `LAYERS`.

## The loop

1. **Write** the graph as a `.py` file.
2. **Inspect** — `depsgx inspect deps.py`. It prints the modules, roots, layers,
   and every problem with a stable `code`, and writes `<name>.storyboard.png`.
   **Exit 1 means at least one error.**
3. **Fix** and inspect again. View the storyboard: each numbered box marks a
   faulty module.
4. **Render** — `depsgx render deps.py -o deps.png`.

## Reading the report

- `error` — the architecture is broken: `cycle`, `layer-violation`,
  `forbidden-dependency`, `self-dependency`, `dangling-dependency`. Exit code 1.
- `info` — dead code (`unreachable-module`, `orphan-module`) or configuration
  notes (`duplicate-dependency`, `no-roots`).

`depends` points from a module to what it imports, so a cycle is a real
circular import, and a layer violation is a lower layer importing a higher one.
