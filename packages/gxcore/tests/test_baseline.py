"""The baseline: a report compared to an accepted past state.

A checker that always fails on old debt gets switched off. These tests pin the
promise: a baseline records the accepted problems, a re-run tells you what is
new, fixed, or unchanged, and CI fails only on the new errors.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from gxcore.baseline import Baseline, compare, fingerprint, summary
from gxcore.cli import Tool, run
from gxcore.model import ERROR, INFO, WARN, Problem, Report


def _report(*problems, name="r"):
    return Report(name, problems=list(problems))


def _tool(report):
    return Tool(
        name="t",
        description="d",
        load=lambda path: object(),
        inspect=lambda artifact: report,
        render=lambda artifact, out, dpi: Path("x"),
    )


def test_fingerprint_is_code_target_and_label_only():
    assert fingerprint("a", "t", "l") == "a\x1ft\x1fl"
    assert fingerprint("a", None, "") != fingerprint("a", "t", "")
    assert fingerprint("a", "t", "l") != fingerprint("a", "t", "m")


def test_baseline_of_records_every_problem():
    report = _report(Problem(ERROR, "a", "msg", target="t", label="lbl"), Problem(INFO, "b", "m"))
    baseline = Baseline.of(report)
    assert baseline.name == "r"
    assert baseline.problems[0] == {
        "code": "a",
        "severity": ERROR,
        "target": "t",
        "label": "lbl",
        "message": "msg",
    }
    assert baseline.problems[1] == {"code": "b", "severity": INFO, "message": "m"}


def test_save_then_load_roundtrips(tmp_path):
    path = tmp_path / "sub" / "baseline.json"
    Baseline.of(_report(Problem(ERROR, "a", "m", target="t"))).save(path)
    loaded = Baseline.load(path)
    assert loaded.name == "r"
    assert loaded.problems == [{"code": "a", "severity": ERROR, "target": "t", "message": "m"}]


def test_load_rejects_an_unknown_version(tmp_path):
    path = tmp_path / "b.json"
    path.write_text('{"version": 99, "problems": []}')
    with pytest.raises(ValueError, match="unsupported baseline version"):
        Baseline.load(path)


def test_compare_classifies_new_fixed_and_unchanged():
    before = Baseline.of(_report(Problem(ERROR, "a", "m", target="t1"), Problem(WARN, "b", "m")))
    report = _report(Problem(ERROR, "a", "m", target="t1"), Problem(ERROR, "c", "m", target="t2"))
    diff = compare(report, before)
    assert [p.code for p in diff.new] == ["c"]
    assert [r["code"] for r in diff.fixed] == ["b"]
    assert [p.code for p in diff.persisted] == ["a"]
    assert diff.new_errors == 1


def test_summary_lists_the_fixed_problems():
    before = Baseline.of(_report(Problem(ERROR, "a", "m", target="t")))
    text = summary(compare(_report(), before))
    assert "1 fixed" in text
    assert "  fixed:" in text
    assert "a" in text


def test_summary_is_one_line_without_fixed():
    baseline = Baseline.of(_report(Problem(WARN, "a", "m")))
    assert summary(compare(_report(Problem(WARN, "a", "m")), baseline)) == (
        "baseline: 0 new, 0 fixed, 1 unchanged"
    )


# --------------------------------------------------------------------------- #
# the CLI contract
# --------------------------------------------------------------------------- #


def test_write_baseline_then_a_clean_rerun_exits_zero(tmp_path, capsys):
    tool = _tool(_report(Problem(ERROR, "boom", "m", target="t")))
    path = tmp_path / "b.json"
    args = ["inspect", "a.py", "--no-storyboard", "--write-baseline", str(path)]
    assert run(tool, args) == 1  # first run has no baseline: the error fails
    assert path.exists()
    assert run(tool, ["inspect", "a.py", "--no-storyboard", "--baseline", str(path)]) == 0
    assert "baseline: 0 new, 0 fixed, 1 unchanged" in capsys.readouterr().out


def test_a_new_error_fails_against_a_baseline(tmp_path):
    path = tmp_path / "b.json"
    Baseline(name="r", problems=[]).save(path)
    tool = _tool(_report(Problem(ERROR, "boom", "m")))
    assert run(tool, ["inspect", "a.py", "--no-storyboard", "--baseline", str(path)]) == 1


def test_a_fixed_error_is_reported_and_does_not_fail(tmp_path, capsys):
    path = tmp_path / "b.json"
    Baseline.of(_report(Problem(ERROR, "old", "m", target="t"))).save(path)
    tool = _tool(Report("r"))
    assert run(tool, ["inspect", "a.py", "--no-storyboard", "--baseline", str(path)]) == 0
    assert "1 fixed" in capsys.readouterr().out


def test_json_includes_the_baseline_diff(tmp_path, capsys):
    path = tmp_path / "b.json"
    Baseline(name="r", problems=[]).save(path)
    tool = _tool(_report(Problem(INFO, "note", "m")))
    args = ["inspect", "a.py", "--no-storyboard", "--json", "--baseline", str(path)]
    assert run(tool, args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["baseline"] == {"new": 1, "fixed": 0, "persisted": 0, "new_errors": 0}


def test_save_and_load_roundtrip_non_ascii(tmp_path):
    path = tmp_path / "b.json"
    Baseline.of(_report(Problem(ERROR, "code", "エラー — 日本語", target="セルr2c3"))).save(path)
    loaded = Baseline.load(path)
    assert loaded.problems[0]["message"] == "エラー — 日本語"
    assert loaded.problems[0]["target"] == "セルr2c3"
