"""A coherent configuration that should pass."""

import envgx as e

NAME = "Service config"

env = e.Environment(
    variables=[
        e.Variable("DATABASE_URL", type="str", required=True, secret=True),
        e.Variable("PORT", type="int", default="8080"),
    ],
    references=["DATABASE_URL", "PORT"],
)
