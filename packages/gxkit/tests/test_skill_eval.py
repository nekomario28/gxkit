"""The skill evaluation's grader, fed the outcomes it must tell apart.

The evaluation itself needs a model, so it is not in the gate — which would leave
its *grading* unguarded. This is that guard: four directories, one per outcome an
agent can leave behind, and the verdict each must get. A grader that passes a
deletion would make every future evaluation worthless.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _module():
    path = ROOT / "scripts" / "skill_eval.py"
    spec = importlib.util.spec_from_file_location("skill_eval", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # `@dataclass` looks its class up in `sys.modules`; a module loaded from a path
    # is not there yet, and the lookup would find nothing.
    sys.modules["skill_eval"] = module
    spec.loader.exec_module(module)
    return module


EVAL = _module()
LEVEL = next(task for task in EVAL.TASKS if task.name == "levelgx")
CHART = next(task for task in EVAL.TASKS if task.name == "chartgx")


def _setup(task, directory: Path) -> None:
    EVAL.setup(task, directory)


def _problems(task, directory: Path) -> list[str]:
    return EVAL.task_problems(task, directory, EVAL.sources_digest())


def test_an_untouched_artifact_fails(tmp_path):
    for task in (LEVEL, CHART):
        directory = tmp_path / task.name
        _setup(task, directory)
        problems = _problems(task, directory)
        assert problems, f"{task.name}: the broken artifact passed"


def test_a_correct_fix_passes(tmp_path):
    level = tmp_path / "level"
    _setup(LEVEL, level)
    # The fix the independent agent actually made: the second `>` becomes a floor.
    (level / "puzzle.py").write_text(
        '"""The vault level."""\nLEVEL = [\n    "S.G##",\n    ".>.X#",\n]\n', encoding="utf-8"
    )
    assert _problems(LEVEL, level) == []

    chart = tmp_path / "chart"
    _setup(CHART, chart)
    model = json.loads((chart / "quarterly.json").read_text(encoding="utf-8"))
    model["y_min"] = 0
    (chart / "quarterly.json").write_text(json.dumps(model), encoding="utf-8")
    assert _problems(CHART, chart) == []


def test_deleting_the_artifact_fails(tmp_path):
    for task in (LEVEL, CHART):
        directory = tmp_path / task.name
        _setup(task, directory)
        (directory / task.filename).unlink()
        assert _problems(task, directory) == [f"{task.filename} was deleted"]


def test_removing_what_the_artifact_is_about_fails(tmp_path):
    """A fix that deletes the item, the goal or the data solves nothing."""
    level = tmp_path / "level"
    _setup(LEVEL, level)
    (level / "puzzle.py").write_text(
        '"""The vault level."""\nLEVEL = [\n    "S.G##",\n    ".>.##",\n]\n', encoding="utf-8"
    )
    problems = _problems(LEVEL, level)
    assert any("item tile" in problem for problem in problems), problems

    chart = tmp_path / "chart"
    _setup(CHART, chart)
    model = json.loads((chart / "quarterly.json").read_text(encoding="utf-8"))
    model["marks"][0]["values"] = [0.0, 0.0, 0.0, 0.0]
    (chart / "quarterly.json").write_text(json.dumps(model), encoding="utf-8")
    problems = _problems(CHART, chart)
    assert any("values were changed" in problem for problem in problems), problems


def test_patching_the_tool_is_seen(tmp_path):
    """The check is a digest of the tool sources, so a patched tool cannot pass."""
    directory = tmp_path / "level"
    _setup(LEVEL, directory)
    (directory / "puzzle.py").write_text(
        '"""The vault level."""\nLEVEL = [\n    "S.G##",\n    ".>.X#",\n]\n', encoding="utf-8"
    )
    assert EVAL.task_problems(LEVEL, directory, "0" * 64) != []


def test_the_fixtures_are_what_the_tasks_claim(tmp_path):
    """Each fixture fails for the reason its task documents."""
    from levelgx import inspect_level, load_level

    directory = tmp_path / "level"
    _setup(LEVEL, directory)
    level, _loaded = load_level(directory / "puzzle.py")
    assert _loaded is not None
    report = inspect_level(level)
    assert [problem.code for problem in report.problems] == ["soft-lock"]

    from chartgx.model import inspect_model, load_model

    directory = tmp_path / "chart"
    _setup(CHART, directory)
    model = load_model(directory / "quarterly.json")
    codes = [
        problem.code for problem in inspect_model(model).problems if problem.severity == "error"
    ]
    assert codes == ["truncated-baseline"]


def test_every_task_names_a_tool_that_exists(tmp_path):
    for task in EVAL.TASKS:
        assert (ROOT / "packages" / task.tool / "SKILL.md").is_file()
        assert task.body.strip()
        directory = tmp_path / task.name
        _setup(task, directory)
        assert (directory / task.filename).is_file()
        assert "SKILL.md" in (directory / "PROMPT.txt").read_text(encoding="utf-8")


def test_the_prompt_forbids_editing_the_skill():
    """Without this the evaluation would grade an agent that rewrote the rules."""
    assert "do not edit, delete or bypass `SKILL.md`" in EVAL.PROMPT
    # The artifact is filled in per task, so the prompt names a placeholder.
    assert "{artifact}" in EVAL.PROMPT
    for task in EVAL.TASKS:
        assert task.filename in EVAL.PROMPT.format(artifact=task.filename)
