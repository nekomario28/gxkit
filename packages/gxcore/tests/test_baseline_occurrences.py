"""Baselines must not discard repeated findings that share a display location."""

from gxcore.baseline import Baseline, compare
from gxcore.model import ERROR, Problem, Report


def test_an_additional_occurrence_is_a_new_error():
    first = Problem(ERROR, "overlap", "first", target="c", label="c")
    second = Problem(ERROR, "overlap", "second", target="c", label="c")
    baseline = Baseline.of(Report("r", problems=[first]))
    diff = compare(Report("r", problems=[first, second]), baseline)
    assert diff.new == [second]
    assert diff.persisted == [first]
    assert diff.new_errors == 1


def test_removing_one_occurrence_preserves_the_other():
    first = Problem(ERROR, "overlap", "first", target="c", label="c")
    second = Problem(ERROR, "overlap", "second", target="c", label="c")
    diff = compare(
        Report("r", problems=[first]), Baseline.of(Report("r", problems=[first, second]))
    )
    assert diff.persisted == [first]
    assert [p["message"] for p in diff.fixed] == ["second"]
    assert diff.new_errors == 0


def test_domain_identity_survives_reordered_targets_and_numeric_prose(tmp_path):
    before = Problem(
        ERROR, "overlap", "a/c at 5", target="r[2]", label="c", identity=("r", "a", "c")
    )
    after = Problem(
        ERROR, "overlap", "a/c at 7", target="r[0]", label="a", identity=("r", "a", "c")
    )
    path = tmp_path / "baseline.json"
    Baseline.of(Report("r", problems=[before])).save(path)
    baseline = Baseline.load(path)
    assert baseline.problems[0]["identity"] == ["r", "a", "c"]
    assert after.as_dict()["identity"] == ["r", "a", "c"]
    diff = compare(Report("r", problems=[after]), baseline)
    assert diff.persisted == [after]
    assert diff.new == diff.fixed == []


def test_ambiguous_version_one_baseline_is_rejected(tmp_path):
    import pytest

    path = tmp_path / "old.json"
    path.write_text('{"version": 1, "problems": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="recreate it with --write-baseline"):
        Baseline.load(path)
