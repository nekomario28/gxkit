"""A schedule that should pass: runs share a resource only back-to-back."""

import crongx as c

NAME = "Nightly"

schedule = c.Schedule(
    runs=[
        c.Run("backup", start=0, duration=3600, resource="disk"),
        c.Run("reindex", start=3600, duration=1800, resource="disk"),
        c.Run("report", start=0, duration=600, resource="cpu"),
    ]
)
