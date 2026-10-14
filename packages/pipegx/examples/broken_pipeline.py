"""A pipeline with faults.

* `build`/`test` both produce `app`       -> duplicate-artifact
* `test` needs `ghost`, not a step         -> unknown-step
* `test` is declared twice                 -> duplicate-step
* `deploy`/`package` need each other       -> cycle
* the goal `missing.tar` is produced by no step -> goal-not-produced
"""

import pipegx as p

NAME = "Build"

pipeline = p.Pipeline(
    steps=[
        p.Step("build", produces=["app"]),
        p.Step("test", needs=["ghost"], produces=["app"]),
        p.Step("test", needs=["build"]),
        p.Step("deploy", needs=["package"]),
        p.Step("package", needs=["deploy"], produces=["app.tar"]),
    ],
    goals=["missing.tar"],
)
