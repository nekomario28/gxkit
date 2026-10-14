"""crongx's domain knowledge: can this schedule run without collision?

Interval overlap on a shared resource is the whole question; a run with no
resource occupies nothing shared and cannot collide.
"""

from __future__ import annotations

from gxcore import ERROR, INFO, Problem, Report

from .model import Schedule
from .render import compute_layout, node_box


def _node_id(index: int) -> str:
    return f"r[{index}]"


def inspect_schedule(schedule: Schedule, name: str | None = None) -> Report:
    name = name or schedule.name
    report = Report(
        name=name,
        subject=f"schedule: {len(schedule.runs)} runs",
        details=[f"{len(schedule.runs)} runs"],
    )
    out: list[Problem] = []

    seen_names: set[str] = set()
    for i, run in enumerate(schedule.runs):
        target = _node_id(i)
        if run.name in seen_names:
            out.append(
                Problem(
                    ERROR,
                    "duplicate-run",
                    f"run {run.name!r} is declared more than once",
                    target=target,
                    label=run.name,
                )
            )
        seen_names.add(run.name)
        if run.start < 0:
            out.append(
                Problem(
                    ERROR,
                    "negative-start",
                    f"{run.name!r} starts at {run.start:g}, before zero",
                    target=target,
                    label=run.name,
                )
            )
        if run.duration < 0:
            out.append(
                Problem(
                    ERROR,
                    "negative-duration",
                    f"{run.name!r} has a duration of {run.duration:g}",
                    target=target,
                    label=run.name,
                )
            )
        if run.duration == 0:
            out.append(
                Problem(
                    INFO,
                    "zero-duration",
                    f"{run.name!r} has zero duration — it never runs",
                    target=target,
                    label=run.name,
                )
            )

    for i in range(len(schedule.runs)):
        for j in range(i + 1, len(schedule.runs)):
            a, b = schedule.runs[i], schedule.runs[j]
            if a.resource and a.resource == b.resource and schedule.overlap(a, b):
                out.append(
                    Problem(
                        ERROR,
                        "overlap",
                        f"{a.name!r} and {b.name!r} both hold {a.resource!r} at once",
                        target=_node_id(j),
                        label=b.name,
                        identity=(a.resource, *sorted((a.name, b.name))),
                    )
                )

    if not schedule.runs:
        out.append(Problem(INFO, "no-runs", "the schedule declares no runs"))

    positions, r = compute_layout(schedule)
    for problem in out:
        if problem.bbox is None and problem.target in positions:
            problem.bbox = node_box(positions[problem.target], r)

    report.problems = out
    return report
