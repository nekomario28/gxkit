"""pipegx's domain knowledge: will this pipeline build and deliver?

The graph questions — cycles, a build order — come from `gxcore.graph`; the
pipeline ones are: every need names a real step, every goal is actually
produced, and no two steps claim the same artifact.
"""

from __future__ import annotations

from gxcore import ERROR, INFO, Problem, Report
from gxcore.graph import cycle_witnesses, topological_sort

from .model import Pipeline
from .render import compute_layout, node_box


def inspect_pipeline(pipeline: Pipeline, name: str | None = None) -> Report:
    name = name or pipeline.name
    declared = set(pipeline.names())
    edges = pipeline.edges()

    report = Report(
        name=name,
        subject=f"pipeline: {len(pipeline.steps)} steps, {len(pipeline.artifacts())} artifacts",
        details=[
            f"{len(pipeline.steps)} steps, {len(pipeline.artifacts())} artifacts",
            "goals: " + (", ".join(pipeline.goals) or "none"),
        ],
    )
    out: list[Problem] = []

    seen_steps: set[str] = set()
    seen_artifacts: dict[str, str] = {}
    for step in pipeline.steps:
        if step.name in seen_steps:
            out.append(
                Problem(
                    ERROR,
                    "duplicate-step",
                    f"step {step.name!r} is declared more than once",
                    target=step.name,
                )
            )
        seen_steps.add(step.name)
        for need in step.needs:
            if declared and need not in declared:
                out.append(
                    Problem(
                        ERROR,
                        "unknown-step",
                        f"{step.name!r} needs {need!r}, which is not a step",
                        target=step.name,
                    )
                )
        for artifact in step.produces:
            if artifact in seen_artifacts and seen_artifacts[artifact] != step.name:
                out.append(
                    Problem(
                        ERROR,
                        "duplicate-artifact",
                        f"{artifact!r} is produced by both {seen_artifacts[artifact]!r} "
                        f"and {step.name!r}",
                        target=step.name,
                    )
                )
            seen_artifacts.setdefault(artifact, step.name)

    for goal in pipeline.goals:
        if goal not in seen_artifacts:
            # The goal *is* the finding: two unproduced goals are two defects, and
            # swapping one for another is new debt.
            out.append(
                Problem(
                    ERROR,
                    "goal-not-produced",
                    f"the goal {goal!r} is produced by no step",
                    identity=(goal,),
                )
            )

    for witness, component in cycle_witnesses(edges):
        out.append(
            Problem(
                ERROR,
                "cycle",
                f"the needs graph has a cycle: {' → '.join(witness)}",
                target=witness[0],
                identity=tuple(component),
            )
        )
    else:
        order = topological_sort(edges)
        if order is not None and len(order) > 1:
            report.details.append("build order: " + " → ".join(reversed(order)))

    if not pipeline.steps:
        out.append(Problem(INFO, "no-steps", "the pipeline declares no steps"))
    if not pipeline.goals:
        out.append(Problem(INFO, "no-goals", "the pipeline declares no goals"))

    positions, r = compute_layout(pipeline)
    for problem in out:
        if problem.bbox is None and problem.target in positions:
            problem.bbox = node_box(positions[problem.target], r)

    report.problems = out
    return report
