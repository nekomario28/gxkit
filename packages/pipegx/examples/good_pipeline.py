"""A pipeline that should pass: a DAG, real needs, produced goals."""

import pipegx as p

NAME = "Build"

pipeline = p.Pipeline(
    steps=[
        p.Step("build", produces=["app"]),
        p.Step("test", needs=["build"], produces=["report.xml"]),
        p.Step("package", needs=["build"], produces=["app.tar"]),
    ],
    goals=["app.tar", "report.xml"],
)
