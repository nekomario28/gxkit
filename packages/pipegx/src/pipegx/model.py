"""A build pipeline: steps with their needs and the artifacts they produce.

    import pipegx as p

    pipeline = p.Pipeline(
        steps=[
            p.Step("build", produces=["app"]),
            p.Step("package", needs=["build"], produces=["app.tar"]),
        ],
        goals=["app.tar"],
    )

`needs` are step names; `produces` are file names; `goals` are the artifacts the
pipeline must deliver.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Step:
    name: str
    needs: list[str] = field(default_factory=list)
    produces: list[str] = field(default_factory=list)


@dataclass
class Pipeline:
    steps: list[Step] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)
    name: str = "pipeline"

    def names(self) -> list[str]:
        return [step.name for step in self.steps]

    def edges(self) -> dict[str, list[str]]:
        graph: dict[str, list[str]] = {step.name: [] for step in self.steps}
        for step in self.steps:
            graph.setdefault(step.name, []).extend(step.needs)
            for need in step.needs:
                graph.setdefault(need, [])
        return graph

    def artifacts(self) -> list[str]:
        return [artifact for step in self.steps for artifact in step.produces]


def _as_step(value: object) -> Step | None:
    if isinstance(value, Step):
        return value
    if isinstance(value, str):
        return Step(value)
    if isinstance(value, dict):
        name = value.get("name")
        if name is None:
            return None
        return Step(
            str(name),
            needs=[str(n) for n in value.get("needs", [])],
            produces=[str(p) for p in value.get("produces", [])],
        )
    if isinstance(value, (tuple, list)) and value:
        name = value[0]
        needs = value[1] if len(value) > 1 else []
        return Step(str(name), needs=[str(n) for n in needs])
    return None


def _as_pipeline(value: object) -> Pipeline | None:
    if isinstance(value, Pipeline):
        return value
    if isinstance(value, dict) and "steps" in value:
        steps = [_as_step(item) for item in value["steps"]]
        if any(step is None for step in steps):
            return None
        return Pipeline(
            steps=[step for step in steps if step is not None],
            goals=[str(g) for g in value.get("goals", [])],
            name=str(value.get("name", "pipeline")),
        )
    if isinstance(value, (list, tuple)):
        built: list[Step] = []
        for item in value:
            step = _as_step(item)
            if step is None:
                return None
            built.append(step)
        if built:
            return Pipeline(steps=built)
    return None


def load_pipeline(path: str | Path) -> tuple[Pipeline, object]:
    from gxcore.loading import load_module, resolve

    path = Path(path)
    module = load_module(path)
    pipeline = resolve(
        module,
        attrs=("pipeline", "PIPELINE", "build", "dag"),
        builders=("build_pipeline", "make_pipeline", "make"),
        convert=_as_pipeline,
    )
    if pipeline is None:
        steps = getattr(module, "STEPS", None)
        if steps is not None:
            pipeline = Pipeline(
                steps=[step for step in (_as_step(item) for item in steps) if step is not None],
                goals=[str(g) for g in getattr(module, "GOALS", [])],
            )
    if pipeline is None:
        raise ValueError(
            f"{path}: no pipeline found — define `pipeline` (a Pipeline) or STEPS/GOALS"
        )
    pipeline.name = getattr(module, "NAME", path.stem)
    return pipeline, module


def pipeline_from_parts(
    steps: list[Step] | None = None,
    goals: list[str] | None = None,
    name: str = "pipeline",
) -> Pipeline:
    return Pipeline(steps=list(steps or []), goals=list(goals or []), name=name)
