"""A registry that should pass: every check is declared once and evaluated once."""

import checkgx as c

NAME = "A registry that holds together"

registry = c.Registry(
    checks=["a_probe_passes", "strings_match", "output_nonempty"],
    evaluated=["a_probe_passes", "strings_match", "output_nonempty"],
    metadata=["status", "duration_ms"],
)
