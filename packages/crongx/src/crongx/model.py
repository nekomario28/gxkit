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
from pathlib import Path


@dataclass
class Run:
    name: str
    start: float = 0.0
    duration: float = 0.0
    resource: str = ""

    @property
    def end(self) -> float:
        return self.start + self.duration


@dataclass
class Schedule:
    runs: list[Run] = field(default_factory=list)
    name: str = "schedule"

    def names(self) -> list[str]:
        return [run.name for run in self.runs]

    def overlap(self, a: Run, b: Run) -> bool:
        """True when the two runs' half-open intervals overlap."""
        return a.start < b.end and b.start < a.end


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
        parts = [*list(value), 0.0, 0.0, ""]
        return Run(str(parts[0]), float(parts[1]), float(parts[2]), str(parts[3]))
    return None


def _as_schedule(value: object) -> Schedule | None:
    if isinstance(value, Schedule):
        return value
    if isinstance(value, dict) and "runs" in value:
        runs = [_as_run(item) for item in value["runs"]]
        if any(run is None for run in runs):
            return None
        return Schedule(
            runs=[run for run in runs if run is not None],
            name=str(value.get("name", "schedule")),
        )
    if isinstance(value, (list, tuple)):
        built: list[Run] = []
        for item in value:
            run = _as_run(item)
            if run is None:
                return None
            built.append(run)
        if built:
            return Schedule(runs=built)
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
            schedule = Schedule(
                runs=[run for run in (_as_run(item) for item in runs) if run is not None]
            )
    if schedule is None:
        raise ValueError(f"{path}: no schedule found — define `schedule` (a Schedule) or RUNS")
    schedule.name = getattr(module, "NAME", path.stem)
    return schedule, module


def schedule_from_parts(runs: list[Run] | None = None, name: str = "schedule") -> Schedule:
    return Schedule(runs=list(runs or []), name=name)
