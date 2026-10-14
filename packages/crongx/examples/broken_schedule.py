"""A schedule with faults.

* `backup` and `reindex` both hold `disk` at once -> overlap
* `backup` is declared twice                       -> duplicate-run
* `purge` starts at -60                            -> negative-start
* `probe` has a duration of -5                     -> negative-duration
"""

import crongx as c

NAME = "Nightly"

schedule = c.Schedule(
    runs=[
        c.Run("backup", start=0, duration=3600, resource="disk"),
        c.Run("reindex", start=1800, duration=3600, resource="disk"),
        c.Run("backup", start=7200, duration=600, resource="disk"),
        c.Run("purge", start=-60, duration=300),
        c.Run("probe", start=0, duration=-5),
    ]
)
