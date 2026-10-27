"""A registry whose coverage is not coverage.

* `strings_match` is written twice — a mapping keeps one of them   -> duplicate-check
* `status` is a check name sitting in the metadata mapping         -> check-in-metadata
* `output_nonempty` is declared and nothing evaluates it           -> check-never-evaluated
* `stdout_is_json` is evaluated and nothing declares it            -> evaluated-but-undeclared
"""

import checkgx as c

NAME = "A registry that reads as coverage"

registry = c.Registry(
    checks=[
        "a_probe_passes",
        "strings_match",
        "strings_match",
        "status",
        "output_nonempty",
    ],
    evaluated=["a_probe_passes", "strings_match", "stdout_is_json"],
    metadata=["status", "result_is_json"],
)
