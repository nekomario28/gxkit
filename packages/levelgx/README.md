# levelgx

**Inspect game levels for reachability, solvability and soft-locks.** Write a
level as a grid of characters; `levelgx inspect` flood-fills from the spawn,
proves the goal is solvable, finds stranded items, and — because one-way tiles
make the level a *directed* graph — catches **soft-locks**: cells you can enter
but never leave with the goal still reachable.

One of the [`gxkit`](../../README.md) tools, built on [`gxcore`](../gxcore).

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/levelgx" levelgx inspect level.py
# local:  uvx --from ../../packages/levelgx levelgx inspect level.py
```

## The legend

```
#  wall          .  floor         (space) also floor
S  spawn         G  goal
X  item          !  hazard (deadly: not walkable)
>  one-way east  <  one-way west
v  one-way south ^  one-way north
```

A one-way tile can only be entered moving its way and left moving its way — e.g.
`>` is entered from the west and exited east. Arrows are what create soft-locks.

## Writing a level

```python
NAME = "Two rooms, one key each"

rows = [
    "#########",
    "#S......#",
    "#.#####.#",
    "#X....#G#",
    "#########",
]
```

## The contract

```
$ levelgx inspect softlock_level.py
softlock_level.py: The one-way drop
level: 7x5
storyboard: The_one-way_drop.storyboard.png
  7x5, 1 items, 0 hazards, 1 one-way tiles
  reachable from spawn: 11/11 floor cells
  shortest path to goal: 4 steps
inspect: 1 problem (1 error)
  [1] error cell r2c3  soft-lock: 2 reachable cells cannot get back to the
      goal (e.g. cell r2c3) — a one-way tile makes a dead end
```

- **Exit code 1** when any `error`-severity problem is found.
- `--json` prints the same report machine-readably; `--no-storyboard` skips the
  image; `-o name.png` names it.

## Checks

| code | severity | what it means |
| --- | --- | --- |
| `no-spawn` | error | there is no `S` tile |
| `no-goal` | error | there is no `G` tile |
| `goal-unreachable` | error | the goal cannot be reached from the spawn |
| `soft-lock` | error | reachable cells from which the goal is no longer reachable |
| `stranded-item` | error | an item cannot be reached from the spawn |
| `hazard-cuts-off` | warn | a hazard blocks the only route to the goal |
| `unreachable-area` | info | floor the player can never reach |
| `no-items` | info | the level has nothing to collect |

## Why it can be trusted

Every check is proven to fire on a level with the defect and to stay quiet on one
without (`tests/`), including the directed-graph soft-lock — which a screenshot
review can never catch.

MIT licensed.
