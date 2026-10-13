"""A soft-lock: the level is solvable, but one branch traps the player.

The one-way `v` at r2c3 only lets an actor move *south*. Step onto it and you
are pushed into the pocket at r3c3, from which north is blocked and every other
side is a wall — the goal can never be reached again. `levelgx` reports it as
`soft-lock` (error), which a screenshot review would never catch.
"""

NAME = "The one-way drop"

rows = [
    "#######",
    "#S...G#",
    "#.#v#.#",
    "#X#.#.#",
    "#######",
]
