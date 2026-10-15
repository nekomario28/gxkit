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

from gxcore.loading import convert_items, convert_names


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
        if len(value) > 2:
            return None
        name = value[0]
        needs = value[1] if len(value) > 1 else []
        return Step(str(name), needs=[str(n) for n in needs])
    return None


def _as_pipeline(value: object) -> Pipeline | None:
    if isinstance(value, Pipeline):
        value.steps = convert_items(value.steps, _as_step, field="steps")
        return value
    if isinstance(value, dict) and "steps" in value:
        return Pipeline(
            steps=convert_items(value["steps"], _as_step, field="steps"),
            goals=convert_names(value.get("goals", []), field="goals"),
            name=str(value.get("name", "pipeline")),
        )
    if isinstance(value, (list, tuple)):
        return Pipeline(steps=convert_items(value, _as_step, field="steps"))
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
                steps=convert_items(steps, _as_step, field="STEPS"),
                goals=convert_names(getattr(module, "GOALS", []), field="GOALS"),
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
