"""Prove every crongx check fires on a schedule that has the fault and stays quiet otherwise."""

from __future__ import annotations

import random
from pathlib import Path

from crongx import Run, Schedule, inspect_schedule, load_schedule, schedule_from_parts
from gxcore import ERROR, INFO
from gxcore.geometry import overlap as box_overlap
from gxcore.testing import assert_fires, assert_quiet


def test_a_clean_schedule_has_no_problems():
    schedule = Schedule(
        runs=[
            Run("backup", start=0, duration=3600, resource="disk"),
            Run("reindex", start=3600, duration=1800, resource="disk"),
        ]
    )
    assert inspect_schedule(schedule).problems == []


def test_overlap():
    schedule = Schedule(
        runs=[
            Run("a", start=0, duration=100, resource="disk"),
            Run("b", start=50, duration=100, resource="disk"),
        ]
    )
    assert_fires(inspect_schedule(schedule), "overlap", ERROR)


def test_touching_runs_do_not_overlap():
    schedule = Schedule(
        runs=[
            Run("a", start=0, duration=100, resource="disk"),
            Run("b", start=100, duration=100, resource="disk"),
        ]
    )
    assert_quiet(inspect_schedule(schedule), "overlap")


def test_different_resources_do_not_overlap():
    schedule = Schedule(
        runs=[
            Run("a", start=0, duration=100, resource="disk"),
            Run("b", start=0, duration=100, resource="cpu"),
        ]
    )
    assert_quiet(inspect_schedule(schedule), "overlap")


def test_duplicate_run():
    schedule = Schedule(runs=[Run("a", duration=1), Run("a", duration=1)])
    assert_fires(inspect_schedule(schedule), "duplicate-run", ERROR)


def test_negative_start():
    assert_fires(
        inspect_schedule(Schedule(runs=[Run("a", start=-1, duration=1)])), "negative-start", ERROR
    )


def test_negative_duration():
    assert_fires(
        inspect_schedule(Schedule(runs=[Run("a", duration=-1)])), "negative-duration", ERROR
    )


def test_zero_duration():
    assert_fires(inspect_schedule(Schedule(runs=[Run("a", duration=0)])), "zero-duration", INFO)


def test_no_runs():
    assert_fires(inspect_schedule(Schedule()), "no-runs", INFO)


def test_schedule_from_parts_roundtrips():
    schedule = schedule_from_parts(runs=[Run("a", duration=1)], name="x")
    assert schedule.names() == ["a"] and schedule.name == "x"


def test_loader_accepts_runs(tmp_path):
    src = tmp_path / "s.py"
    src.write_text(
        'RUNS = [("a", 0, 10, "disk"), {"name": "b", "start": 20, "duration": 5}]\nNAME = "x"\n'
    )
    schedule, _module = load_schedule(src)
    assert schedule.names() == ["a", "b"]
    assert schedule.runs[0].resource == "disk"
    assert schedule.name == "x"


def test_loader_accepts_a_dict(tmp_path):
    src = tmp_path / "s.py"
    src.write_text('SCHEDULE = {"runs": [{"name": "a", "duration": 1}]}\n')
    schedule, _module = load_schedule(src)
    assert schedule.names() == ["a"]


def test_converters():
    from crongx.model import _as_run, _as_schedule

    run = Run("a")
    assert _as_run(run) is run
    assert _as_run("a").name == "a"
    assert _as_run({"name": "a", "duration": 2}).duration == 2
    assert _as_run(("a", 1, 2, "disk")).resource == "disk"
    assert _as_run(("a",)).start == 0.0
    assert _as_run({"duration": 1}) is None
    assert _as_run(42) is None
    schedule = Schedule(runs=[run])
    assert _as_schedule(schedule) is schedule
    assert _as_schedule([("a",)]) is not None
    assert _as_schedule([42]) is None
    assert _as_schedule({"runs": [42]}) is None
    assert _as_schedule(42) is None


def test_image_size_tracks_the_run_count():
    from crongx.render import image_size

    assert image_size(Schedule(runs=[Run("a")]))[0] > 0


def test_overlap_matches_the_box_definition():
    rng = random.Random(7)
    for _ in range(500):
        a = Run("a", start=rng.uniform(0, 100), duration=rng.uniform(0.1, 50), resource="r")
        b = Run("b", start=rng.uniform(0, 100), duration=rng.uniform(0.1, 50), resource="r")
        boxes_overlap = box_overlap((a.start, 0.0, a.end, 1.0), (b.start, 0.0, b.end, 1.0)) > 0.0
        assert Schedule().overlap(a, b) == boxes_overlap


def test_examples_load_and_are_diagnosed():
    examples = Path(__file__).resolve().parents[1] / "examples"
    good, _ = load_schedule(examples / "good_schedule.py")
    broken, _ = load_schedule(examples / "broken_schedule.py")
    assert inspect_schedule(good).errors == 0
    report = inspect_schedule(broken)
    for code in ("overlap", "duplicate-run", "negative-start", "negative-duration"):
        assert_fires(report, code, ERROR)
