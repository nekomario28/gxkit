"""envgx's domain knowledge: is this configuration coherent and safe?

Configuration drift is the same problem as a schema: a reference to something
undeclared, or a declaration nothing uses. Add the config-specific ones: a secret
with a default (it leaks into source), a type that is not real, and a required
variable that also has a default (a contradiction).
"""

from __future__ import annotations

from gxcore import ERROR, INFO, WARN, Problem, Report

from .model import TYPES, Environment
from .render import compute_layout, node_box


def _node_id(index: int) -> str:
    return f"v[{index}]"


def inspect_environment(env: Environment, name: str | None = None) -> Report:
    name = name or env.name
    report = Report(
        name=name,
        subject=f"env: {len(env.variables)} variables",
        details=[f"{len(env.variables)} variables", f"{len(env.references)} references"],
    )
    out: list[Problem] = []

    declared: dict[str, int] = {}
    for i, variable in enumerate(env.variables):
        target = _node_id(i)
        if not variable.name.strip():
            out.append(Problem(ERROR, "empty-name", "a variable has an empty name", target=target))
        if variable.name in declared:
            out.append(
                Problem(
                    ERROR,
                    "duplicate-variable",
                    f"{variable.name} is declared more than once",
                    target=target,
                    label=variable.name,
                )
            )
        declared[variable.name] = i
        if variable.type not in TYPES:
            out.append(
                Problem(
                    ERROR,
                    "unknown-type",
                    f"{variable.name} has type {variable.type!r}; use one of {', '.join(TYPES)}",
                    target=target,
                    label=variable.name,
                )
            )
        if variable.secret and variable.default is not None:
            out.append(
                Problem(
                    ERROR,
                    "secret-with-default",
                    f"{variable.name} is secret but has a default — the secret would be in source",
                    target=target,
                    label=variable.name,
                )
            )
        if variable.required and variable.default is not None:
            out.append(
                Problem(
                    WARN,
                    "required-with-default",
                    f"{variable.name} is required but also has a default — pick one",
                    target=target,
                    label=variable.name,
                )
            )

    for reference in env.references:
        if declared and reference not in declared:
            out.append(
                Problem(
                    ERROR,
                    "undeclared-reference",
                    f"the code reads {reference!r}, which is not declared",
                    label=reference,
                )
            )

    used = set(env.references)
    if env.references:
        for i, variable in enumerate(env.variables):
            if variable.name not in used:
                out.append(
                    Problem(
                        INFO,
                        "unused-variable",
                        f"{variable.name} is declared but never read",
                        target=_node_id(i),
                        label=variable.name,
                    )
                )

    if not env.variables:
        out.append(Problem(INFO, "no-variables", "the environment declares no variables"))

    positions, r = compute_layout(env)
    for problem in out:
        if problem.bbox is None and problem.target in positions:
            problem.bbox = node_box(positions[problem.target], r)

    report.problems = out
    return report
