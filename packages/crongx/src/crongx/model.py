"""A schedule of timed runs, each on a shared resource.

    import crongx as c

    schedule = c.Schedule(runs=[
        c.Run("backup", start=0, duration=3600, resource="disk"),
        c.Run("report", start=0, duration=600, resource="cpu"),
    ])

A run occupies ``[start, start + duration)``. Two runs on the same resource must
not overlap, or one is starved while the other holds it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from pathlib import Path

from gxcore.loading import convert_items


@dataclass
class Run:
    name: str
    start: float = 0.0
    duration: float = 0.0
    resource: str = ""

    @property
    def end(self) -> float:
        return self.start + self.duration

    @property
    def is_finite(self) -> bool:
        return all(isfinite(value) for value in (self.start, self.duration, self.end))


@dataclass
class Schedule:
    runs: list[Run] = field(default_factory=list)
    name: str = "schedule"

    def names(self) -> list[str]:
        return [run.name for run in self.runs]

    def overlap(self, a: Run, b: Run) -> bool:
        """True when the two runs' half-open intervals overlap."""
        valid = all(run.is_finite and run.start >= 0 and run.duration > 0 for run in (a, b))
        return valid and a.start < b.end and b.start < a.end


def _as_run(value: object) -> Run | None:
    if isinstance(value, Run):
        return value
    if isinstance(value, str):
        return Run(value)
    if isinstance(value, dict):
        name = value.get("name")
        if name is None:
            return None
        return Run(
            str(name),
            start=float(value.get("start", 0.0)),
            duration=float(value.get("duration", 0.0)),
            resource=str(value.get("resource", "")),
        )
    if isinstance(value, (tuple, list)) and value:
        # (name, start, duration, resource) with the tail optional
        if len(value) > 4:
            return None
        return Run(
            str(value[0]),
            start=float(value[1]) if len(value) > 1 else 0.0,
            duration=float(value[2]) if len(value) > 2 else 0.0,
            resource=str(value[3]) if len(value) > 3 else "",
        )
    return None


def _as_schedule(value: object) -> Schedule | None:
    if isinstance(value, Schedule):
        value.runs = convert_items(value.runs, _as_run, field="runs")
        return value
    if isinstance(value, dict) and "runs" in value:
        return Schedule(
            runs=convert_items(value["runs"], _as_run, field="runs"),
            name=str(value.get("name", "schedule")),
        )
    if isinstance(value, (list, tuple)):
        return Schedule(runs=convert_items(value, _as_run, field="runs"))
    return None


def load_schedule(path: str | Path) -> tuple[Schedule, object]:
    from gxcore.loading import load_module, resolve

    path = Path(path)
    module = load_module(path)
    schedule = resolve(
        module,
        attrs=("schedule", "SCHEDULE", "cron", "plan"),
        builders=("build", "make_schedule", "make"),
        convert=_as_schedule,
    )
    if schedule is None:
        runs = getattr(module, "RUNS", None)
        if runs is not None:
            schedule = Schedule(runs=convert_items(runs, _as_run, field="RUNS"))
    if schedule is None:
        raise ValueError(f"{path}: no schedule found — define `schedule` (a Schedule) or RUNS")
    schedule.name = getattr(module, "NAME", path.stem)
    return schedule, module


def schedule_from_parts(runs: list[Run] | None = None, name: str = "schedule") -> Schedule:
    return Schedule(runs=list(runs or []), name=name)
