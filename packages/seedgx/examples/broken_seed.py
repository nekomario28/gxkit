"""A manifest with faults.

* `numpy` has no seed                          -> missing-seed
* `jax` seed is 2**32, out of range             -> seed-out-of-range
* `torch` reuses python's seed 42               -> duplicate-seed
* `torch` is declared twice                      -> duplicate-stream
* the manifest is marked non-deterministic       -> non-deterministic
"""

import seedgx as s

NAME = "Training"

spec = s.SeedSpec(
    streams=[
        s.Stream("python", 42),
        s.Stream("numpy", None),
        s.Stream("torch", 42),
        s.Stream("torch", 1),
        s.Stream("jax", 2**32),
    ],
    deterministic=False,
)
