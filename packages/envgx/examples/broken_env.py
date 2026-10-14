"""A configuration with drift.

* `DATABASE_URL` is secret but has a default      -> secret-with-default
* `PORT` is typed `integer`, which is not real     -> unknown-type
* `PORT` is declared twice                         -> duplicate-variable
* the code reads `MISSING`, which is not declared  -> undeclared-reference
* `DEBUG` is required and has a default            -> required-with-default
* `PORT`/`DEBUG` are declared but never read        -> unused-variable
"""

import envgx as e

NAME = "Service config"

env = e.Environment(
    variables=[
        e.Variable("DATABASE_URL", secret=True, default="postgres://localhost"),
        e.Variable("PORT", type="integer", default="8080"),
        e.Variable("PORT", type="int"),
        e.Variable("DEBUG", required=True, default="true"),
    ],
    references=["DATABASE_URL", "MISSING"],
)
