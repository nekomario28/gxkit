"""`.gxkit.toml`: ignore a code, or change a severity."""

from __future__ import annotations

from gxcore import ERROR, INFO, WARN, Problem, Report
from gxcore.config import Config, apply, find, load


def make_report():
    return Report("r", problems=[
        Problem(ERROR, "soft-lock", "stuck"),
        Problem(WARN, "dual-axis", "two scales"),
        Problem(INFO, "no-units", "no unit"),
    ])


def test_ignore_drops_a_code():
    r = apply(make_report(), Config(ignore={"no-units"}), "levelgx")
    assert {p.code for p in r.problems} == {"soft-lock", "dual-axis"}


def test_severity_override_changes_the_verdict():
    r = apply(make_report(), Config(severity={"dual-axis": "error"}), "levelgx")
    assert r.errors == 2
    r = apply(make_report(), Config(severity={"soft-lock": "warn"}), "levelgx")
    assert r.errors == 0


def test_invalid_severity_is_ignored():
    r = apply(make_report(), Config(severity={"dual-axis": "fatal"}), "levelgx")
    assert {p.severity for p in r.problems} == {"error", "warn", "info"}


def test_per_tool_section_applies_only_to_that_tool():
    cfg = Config(per_tool={"chartgx": {"ignore": ["dual-axis"]}})
    assert {p.code for p in apply(make_report(), cfg, "chartgx").problems} == {
        "soft-lock", "no-units"}
    assert len(apply(make_report(), cfg, "levelgx").problems) == 3


def test_load_reads_the_nearest_file(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".gxkit.toml").write_text('ignore = ["no-units"]\n[chartgx]\nseverity = { "nope" = "x" }\n')
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert find(nested) == tmp_path / ".gxkit.toml"
    cfg = load(nested)
    assert cfg.ignore == {"no-units"}
    assert "chartgx" in cfg.per_tool


def test_no_config_is_empty(tmp_path):
    (tmp_path / ".git").mkdir()
    assert load(tmp_path) == Config()
    assert find(tmp_path) is None


def test_cli_applies_config(tmp_path):
    from gxcore.cli import Tool, run
    from PIL import Image

    (tmp_path / ".gxkit.toml").write_text('severity = { "dual-axis" = "error" }\n')
    src = tmp_path / "x.py"
    src.write_text("")

    def inspect_warn_only(_):
        return Report("r", problems=[Problem(WARN, "dual-axis", "two scales")])

    tool = Tool("t", "d", load=lambda p: None, inspect=inspect_warn_only,
                render=lambda a, o, d: o, to_image=lambda a: Image.new("RGB", (10, 10)))
    assert run(tool, ["inspect", str(src), "--no-storyboard"]) == 1        # upgraded by config
    assert run(tool, ["inspect", str(src), "--no-storyboard", "--no-config"]) == 0
