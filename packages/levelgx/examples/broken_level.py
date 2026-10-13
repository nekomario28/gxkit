"""A level with a hazard on the only route: the goal is unreachable.

The hazard at r1c4 splits the corridor. `goal-unreachable` (error) and
`hazard-cuts-off` (warn) both fire, and the far room is `unreachable-area`.
"""

NAME = "The hazard that cut the level in two"

rows = [
    "#########",
    "#S..!...#",
    "#.#####.#",
    "#X....#G#",
    "#########",
]
