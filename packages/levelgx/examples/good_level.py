"""A level that should pass: the goal is solvable and both items are reachable.

    #  wall   .  floor   S  spawn   G  goal   X  item   !  hazard
    >  <  ^  v  one-way tiles
"""

NAME = "Two rooms, one key each"

rows = [
    "#########",
    "#S......#",
    "#.#####.#",
    "#X....#G#",
    "#########",
]
