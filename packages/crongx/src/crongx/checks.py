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
        if not run.is_finite:
            out.append(
                Problem(
                    ERROR,
                    "non-finite-time",
                    f"{run.name!r} must have finite start, duration, and end",
                    target=target,
                    label=run.name,
                )
            )
            continue
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

    # Sweep by start time: a run can only overlap one that starts before it ends, so the
    # inner scan is bounded by the runs still open. Measured, 100 000 non-overlapping runs
    # never returned from the old double loop (5 000 took 8.3 s, 10 000 took 33.8 s) —
    # every pair was compared to find nothing.
    by_start = sorted(range(len(schedule.runs)), key=lambda index: schedule.runs[index].start)
    open_runs: list[int] = []
    found: list[tuple[int, int, Problem]] = []
    for i in by_start:
        b = schedule.runs[i]
        open_runs = [index for index in open_runs if schedule.runs[index].end > b.start]
        for j in open_runs:
            a = schedule.runs[j]
            if a.resource and a.resource == b.resource and schedule.overlap(a, b):
                first, second = sorted((i, j))
                found.append(
                    (
                        first,
                        second,
                        Problem(
                            ERROR,
                            "overlap",
                            f"{a.name!r} and {b.name!r} both hold {a.resource!r} at once",
                            target=_node_id(second),
                            label=b.name,
                            identity=(a.resource, *sorted((a.name, b.name))),
                        ),
                    )
                )
        open_runs.append(i)
    out.extend(problem for _first, _second, problem in sorted(found, key=lambda item: item[:2]))

    if not schedule.runs:
        out.append(Problem(INFO, "no-runs", "the schedule declares no runs"))

    positions, r = compute_layout(schedule)
    for problem in out:
        if problem.bbox is None and problem.target in positions:
            problem.bbox = node_box(positions[problem.target], r)

    report.problems = out
    return report
