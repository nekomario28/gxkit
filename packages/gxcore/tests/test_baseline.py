"""The baseline: a report compared to an accepted past state.

A checker that always fails on old debt gets switched off. These tests pin the
promise: a baseline records the accepted problems, a re-run tells you what is
new, fixed, or unchanged, and CI fails only on the new errors.
"""

from __future__ import annotations

import copy
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
    assert fingerprint("a", "t", "l") != fingerprint("b", "t", "l")
    assert fingerprint("a\x1ft", "", "l") != fingerprint("a", "t", "l")
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


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ([1, 2], "expected a JSON object"),
        ({"version": 2, "problems": {"a": {}}}, "problems: expected a list"),
        ({"version": 2, "problems": ["x"]}, r"problems\[0\]: expected an object"),
        ({"version": 2, "problems": [{"severity": "error"}]}, r"problems\[0\]\.code"),
        ({"version": 2, "problems": [{"code": "c"}]}, r"problems\[0\]\.severity"),
        ({"version": 2, "problems": [{"code": 3, "severity": "error"}]}, r"problems\[0\]\.code"),
    ],
)
def test_a_baseline_that_cannot_be_read_is_refused_with_its_field(tmp_path, payload, expected):
    """A record this cannot read never matches, so a corrupt baseline would
    report every finding as fixed or new."""
    import json

    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match=expected):
        Baseline.load(path)


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


def test_a_record_shape_that_would_match_wrongly_is_refused_with_field_and_index(tmp_path):
    """The contract's sentence, on the fields that decide *which* finding matches.

    Measured before this guard existed: an `identity` written as a string was
    iterated into characters, never matched, and reported the same finding as both
    `new` and `fixed` (and failed the run) although nothing had changed; an
    `identity` written as an int raised a bare `TypeError` naming neither the field
    nor the index.
    """
    report = Report(
        name="x",
        problems=[
            Problem(ERROR, "a", "first", target="r1", label="one", identity=("a", "b")),
            Problem(ERROR, "b", "second"),
        ],
    )
    path = tmp_path / "base.json"
    Baseline.of(report).save(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    # The records are sorted by (severity, target), so the one with the identity is
    # not first — find them by code rather than by position.
    records = data["problems"]
    located = next(index for index, record in enumerate(records) if record["code"] == "a")
    bare = next(index for index, record in enumerate(records) if record["code"] == "b")
    assert records[located]["identity"] == ["a", "b"], "a well-shaped baseline"

    cases = [
        (located, "identity", "a string, not a list"),
        (located, "identity", 5),
        (located, "target", 7),
        (bare, "target", ["a"]),
        (located, "label", 3),
    ]
    for index, field, value in cases:
        broken = copy.deepcopy(data)
        broken["problems"][index][field] = value
        path.write_text(json.dumps(broken), encoding="utf-8")
        with pytest.raises(ValueError, match=rf"problems\[{index}\]\.{field}") as caught:
            Baseline.load(path)
        message = str(caught.value)
        assert f"problems[{index}].{field}" in message, (field, value, message)


def test_an_output_that_cannot_be_drawn_is_a_refusal_here(tmp_path, capsys):
    """`-o` names a file; a file that is not written must not read as success.

    In process, because the coverage floor counts what runs *here* — the same
    behaviour reached through a console script is covered by the contract
    conformance suite, but that runs in a subprocess and is invisible to it.
    """
    tool = Tool(
        name="t",
        description="d",
        load=lambda path: object(),
        inspect=lambda artifact: _report(),
        render=lambda artifact, out, dpi: Path("x"),
    )

    def cannot_draw(artifact):
        raise ValueError("no renderer here")

    tool.to_image = cannot_draw

    assert run(tool, ["inspect", "a.py", "-o", str(tmp_path / "sb.png"), "--json"]) == 2
    captured = capsys.readouterr()
    assert "cannot write" in captured.err
    assert not (tmp_path / "sb.png").exists()

    # Without `-o` the storyboard is optional: the report still prints.
    assert run(tool, ["inspect", "a.py", "--no-storyboard", "--json"]) == 0
    assert "problems" in capsys.readouterr().out


def test_the_cli_refuses_a_baseline_written_for_another_tool(tmp_path, capsys):
    """Provenance, at the layer that owns it: a sibling's baseline cannot apply.

    A chartgx baseline compared against a levelgx artifact reported "1 new, 2 fixed",
    which is the failure the shape guard documents — a record that never matches
    reports every finding as new or fixed. In-process so the refusal's own lines are
    covered, which a subprocess test cannot do.
    """
    import subprocess
    import sys

    from gxcore.cli import run

    other = tmp_path / "chart.json"
    other.write_text(
        '{"marks": [{"kind": "bar", "categories": ["a"], "values": [1.0]}], "title": "t"}',
        encoding="utf-8",
    )
    baseline = tmp_path / "chart_base.json"
    written = subprocess.run(
        [
            sys.executable,
            "-c",
            "from gxkit.cli import main; raise SystemExit(main())",
            "inspect",
            "chartgx",
            str(other),
            "--no-storyboard",
            "--write-baseline",
            str(baseline),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert written.returncode in (0, 1), written.stderr

    level = tmp_path / "level.py"
    level.write_text(
        "from levelgx import Level\nlevel = Level(rows=['....', '.S..'])\n", encoding="utf-8"
    )
    from gxkit.codes import CODEBOOK
    from levelgx import TOOL

    scope = {name: set(codes) for name, codes in CODEBOOK.items()}
    scope[""] = {code for codes in CODEBOOK.values() for code in codes}
    code = run(
        TOOL,
        ["inspect", str(level), "--no-storyboard", "--no-config", "--baseline", str(baseline)],
        known_tools={"chartgx", "levelgx"},
        known_codes=scope,
    )
    assert code == 2
    assert "baseline for another one" in capsys.readouterr().err


def test_a_null_identity_is_no_identity_rather_than_a_crash(tmp_path):
    """`identity: null` is legal for every optional field; the loader accepted it.

    `tuple(None)` then crashed `compare` with a bare `TypeError` naming neither the
    field nor the index, which is what the loader's own guard exists to prevent.
    """
    path = tmp_path / "base.json"
    path.write_text(
        json.dumps(
            {
                "version": 2,
                "name": "r",
                "problems": [{"code": "a", "severity": "error", "identity": None}],
            }
        ),
        encoding="utf-8",
    )
    stored = Baseline.load(path)
    report = Report("r", problems=[Problem(ERROR, "a", "m")])
    diff = compare(report, stored)
    assert len(diff.persisted) == 1 and diff.new == []
