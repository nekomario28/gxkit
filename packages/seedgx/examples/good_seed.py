"""A reproducible manifest that should pass."""

import seedgx as s

NAME = "Training"

spec = s.SeedSpec(
    streams=[s.Stream("python", 42), s.Stream("numpy", 7)],
    deterministic=True,
)
