# levelgx, for AI agents

A person pointed you here. `levelgx` checks that a game level is actually
playable before anyone builds art for it: write the level as a grid of
characters, then `levelgx inspect` proves solvability and finds traps.

Part of `gxkit`; the review contract (`inspect`, `--json`, exit codes,
storyboard) is shared with every other tool in the family.

## Set it up

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/levelgx" levelgx --help
# or, from a clone:
uv tool install ./packages/levelgx
```

## Write a level

A Python file with a module-level `rows` (list of strings), `LEVEL`, `level`
(a `Level`), or a `build()` returning one:

```python
NAME = "First room"
rows = [
    "#########",
    "#S......#",
    "#.#####.#",
    "#X....#G#",
    "#########",
]
```

Legend: `#` wall, `.`/space floor, `S` spawn, `G` goal, `X` item, `!` hazard,
and one-way tiles `>` `<` `^` `v`.

## The loop

1. **Write** the level as a `.py` file.
2. **Inspect** — `levelgx inspect level.py`. It prints the size, reachability,
   shortest path to the goal, and every problem with a stable `code`, and writes
   `<name>.storyboard.png`. **Exit 1 means at least one error.**
3. **Fix** and inspect again. View the storyboard: each numbered box marks a
   problem cell.
4. **Render** — `levelgx render level.py -o level.png`.

## Reading the report

- `error` — the level is broken (no spawn/goal, unreachable goal, soft-lock,
  stranded item). Fix it. Exit code 1.
- `warn` — a hazard blocks the only route.
- `info` — dead space, or no items.

The one that matters most is `soft-lock`: a one-way tile creates a cell the
player can enter but never leave while the goal is still reachable. Reachability
alone will not find it; the tool searches the directed graph.
