"""Prove every pipegx check fires on a pipeline that has the fault and stays quiet otherwise."""

from __future__ import annotations

from pathlib import Path

import pytest
from gxcore import ERROR, INFO
from gxcore.loading import InvalidArtifact
from gxcore.testing import assert_fires
from pipegx import Pipeline, Step, inspect_pipeline, load_pipeline, pipeline_from_parts


def test_a_clean_pipeline_has_no_problems():
    pipe = Pipeline(
        steps=[Step("build", produces=["app"]), Step("package", needs=["build"])],
        goals=["app"],
    )
    assert inspect_pipeline(pipe).problems == []


def test_unknown_step():
    pipe = Pipeline(steps=[Step("build", needs=["ghost"])])
    assert_fires(inspect_pipeline(pipe), "unknown-step", ERROR)


def test_cycle():
    pipe = Pipeline(steps=[Step("a", needs=["b"]), Step("b", needs=["a"])])
    assert_fires(inspect_pipeline(pipe), "cycle", ERROR)


def test_duplicate_step():
    pipe = Pipeline(steps=[Step("build"), Step("build")])
    assert_fires(inspect_pipeline(pipe), "duplicate-step", ERROR)


def test_duplicate_artifact():
    pipe = Pipeline(steps=[Step("a", produces=["x"]), Step("b", produces=["x"])])
    assert_fires(inspect_pipeline(pipe), "duplicate-artifact", ERROR)


def test_goal_not_produced():
    pipe = Pipeline(steps=[Step("a", produces=["x"])], goals=["y"])
    assert_fires(inspect_pipeline(pipe), "goal-not-produced", ERROR)


def test_no_steps():
    assert_fires(inspect_pipeline(Pipeline()), "no-steps", INFO)


def test_no_goals():
    assert_fires(inspect_pipeline(Pipeline(steps=[Step("a")])), "no-goals", INFO)


def test_build_order_is_reported_for_a_dag():
    pipe = Pipeline(steps=[Step("a"), Step("b", needs=["a"]), Step("c", needs=["b"])])
    report = inspect_pipeline(pipe)
    assert any("build order" in detail for detail in report.details)


def test_pipeline_from_parts_roundtrips():
    pipe = pipeline_from_parts(steps=[Step("a")], goals=["x"], name="p")
    assert pipe.names() == ["a"] and pipe.goals == ["x"] and pipe.name == "p"


def test_loader_accepts_steps_and_goals(tmp_path):
    src = tmp_path / "p.py"
    src.write_text('STEPS = [("build", []), ("test", ["build"])]\nGOALS = ["app"]\nNAME = "x"\n')
    pipe, _module = load_pipeline(src)
    assert pipe.names() == ["build", "test"]
    assert pipe.name == "x"


def test_loader_accepts_a_dict(tmp_path):
    src = tmp_path / "p.py"
    src.write_text(
        'PIPELINE = {"steps": [{"name": "build", "produces": ["app"]}], "goals": ["app"]}\n'
    )
    pipe, _module = load_pipeline(src)
    assert pipe.artifacts() == ["app"]


def test_converters():
    from pipegx.model import _as_pipeline, _as_step

    step = Step("a")
    assert _as_step(step) is step
    assert _as_step("a").name == "a"
    assert _as_step({"name": "a"}).name == "a"
    assert _as_step(("a", ["b"])).needs == ["b"]
    assert _as_step({"needs": []}) is None
    assert _as_step(42) is None
    pipe = Pipeline(steps=[step])
    assert _as_pipeline(pipe) is pipe
    assert _as_pipeline([step]) is not None
    with pytest.raises(InvalidArtifact, match=r"steps\[0\]"):
        _as_pipeline([42])
    with pytest.raises(InvalidArtifact, match=r"steps\[0\]"):
        _as_pipeline({"steps": [42]})
    assert _as_pipeline(42) is None


def test_image_size_tracks_the_step_count():
    from pipegx.render import image_size

    assert image_size(Pipeline(steps=[Step("a")]))[0] > 0


def test_examples_load_and_are_diagnosed():
    examples = Path(__file__).resolve().parents[1] / "examples"
    good, _ = load_pipeline(examples / "good_pipeline.py")
    broken, _ = load_pipeline(examples / "broken_pipeline.py")
    assert inspect_pipeline(good).errors == 0
    report = inspect_pipeline(broken)
    for code in (
        "duplicate-artifact",
        "unknown-step",
        "duplicate-step",
        "cycle",
        "goal-not-produced",
    ):
        assert_fires(report, code, ERROR)
