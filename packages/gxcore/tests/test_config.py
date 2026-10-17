"""`.gxkit.toml`: ignore a code, or change a severity."""

from __future__ import annotations

import pytest
from gxcore import ERROR, INFO, WARN, Problem, Report
from gxcore.config import Config, apply, find, load


def make_report():
    return Report(
        "r",
        problems=[
            Problem(ERROR, "soft-lock", "stuck"),
            Problem(WARN, "dual-axis", "two scales"),
            Problem(INFO, "no-units", "no unit"),
        ],
    )


def test_ignore_drops_a_code():
    r = apply(make_report(), Config(ignore={"no-units"}), "levelgx")
    assert {p.code for p in r.problems} == {"soft-lock", "dual-axis"}


def test_severity_override_changes_the_verdict():
    r = apply(make_report(), Config(severity={"dual-axis": "error"}), "levelgx")
    assert r.errors == 2
    r = apply(make_report(), Config(severity={"soft-lock": "warn"}), "levelgx")
    assert r.errors == 0


def test_an_invalid_severity_is_refused_rather_than_ignored():
    """It used to be dropped in silence, so the reader thought it applied."""
    with pytest.raises(ValueError, match="not one of"):
        apply(make_report(), Config(severity={"dual-axis": "fatal"}), "levelgx")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('ignore = "soft-lock"\n', "expected a list of code names"),
        ("ignore = [3]\n", "expected a list of code names"),
        ('severity = "error"\n', "expected a table of code -> severity"),
        ('[severity]\nsoft-lock = "errr"\n', "is not one of"),
        ("[severity]\nsoft-lock = 3\n", "is not one of"),
        ('[severity]\nsoft-lock = ["error"]\n', "is not one of"),
        ('ingore = ["soft-lock"]\n', "unrecognised key"),
        ('[chartgx]\nignoer = ["x"]\n', "unrecognised key"),
        ('[chartgx]\nignore = "x"\n', "expected a list of code names"),
    ],
)
def test_a_config_that_cannot_be_understood_is_refused_with_its_field(tmp_path, text, expected):
    """`ignore = "soft-lock"` used to mean the eight characters it contains."""
    (tmp_path / ".gxkit.toml").write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=expected):
        load(tmp_path)


def test_a_well_formed_config_still_loads(tmp_path):
    (tmp_path / ".gxkit.toml").write_text(
        'ignore = ["no-units"]\n[severity]\ndual-axis = "error"\n'
        '[chartgx]\nignore = ["red-green"]\n',
        encoding="utf-8",
    )
    config = load(tmp_path)
    assert config.ignore == {"no-units"}
    assert config.severity == {"dual-axis": "error"}
    assert config.per_tool["chartgx"]["ignore"] == ["red-green"]


def test_per_tool_section_applies_only_to_that_tool():
    cfg = Config(per_tool={"chartgx": {"ignore": ["dual-axis"]}})
    assert {p.code for p in apply(make_report(), cfg, "chartgx").problems} == {
        "soft-lock",
        "no-units",
    }
    assert len(apply(make_report(), cfg, "levelgx").problems) == 3


def test_load_reads_the_nearest_file(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".gxkit.toml").write_text(
        'ignore = ["no-units"]\n[chartgx]\nseverity = { "dual-axis" = "warn" }\n'
    )
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

    tool = Tool(
        "t",
        "d",
        load=lambda p: None,
        inspect=inspect_warn_only,
        render=lambda a, o, d: o,
        to_image=lambda a: Image.new("RGB", (10, 10)),
    )
    assert run(tool, ["inspect", str(src), "--no-storyboard"]) == 1  # upgraded by config
    assert run(tool, ["inspect", str(src), "--no-storyboard", "--no-config"]) == 0


def test_a_table_that_names_no_tool_is_refused_when_the_caller_knows_the_family(tmp_path):
    """`[chartgxx]` looks exactly like a tool table, and does nothing.

    Measured before this guard: a typo'd table name was accepted in silence, so the
    rule inside it was inert — the silent-narrowing failure this module refuses
    everywhere else. Only a caller that knows the family can tell; a single tool
    legitimately sees tables for its siblings in a workspace file.
    """
    (tmp_path / ".gxkit.toml").write_text('[chartgxx]\nignore = ["red-green"]\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r"\[chartgxx\] is not a tool"):
        load(tmp_path, known_tools={"chartgx", "levelgx"})

    # Without the family list the name cannot be judged, so it is kept.
    config = load(tmp_path)
    assert "chartgxx" in config.per_tool, config.per_tool


def test_a_code_name_that_names_no_code_is_refused(tmp_path):
    """A misspelled code is a config that does nothing, and must not look active.

    Measured before this guard: `[severity] no-ylabels = "error"` was accepted, the
    intended gate stayed green, and `ignore = ["soft-lok"]` ignored nothing — in the
    file the user wrote to make the gate stricter, which is the silent-narrowing
    failure this module refuses everywhere else.
    """
    scope = {"": {"no-ylabel", "soft-lock"}, "chartgx": {"no-ylabel"}}
    for text, expected in (
        ('[severity]\nno-ylabels = "error"\n', "no-ylabels"),
        ('ignore = ["soft-lok"]\n', "soft-lok"),
        ('[chartgx]\nignore = ["soft-lock"]\n', "soft-lock"),
    ):
        (tmp_path / ".gxkit.toml").write_text(text, encoding="utf-8")
        with pytest.raises(ValueError, match=expected):
            load(tmp_path, known_tools={"chartgx"}, known_codes=scope)

    # The correctly spelled ones load, and without a codebook nothing is judged.
    (tmp_path / ".gxkit.toml").write_text(
        '[severity]\nno-ylabel = "error"\n[chartgx]\nignore = ["no-ylabel"]\n', encoding="utf-8"
    )
    config = load(tmp_path, known_tools={"chartgx"}, known_codes=scope)
    assert config.severity == {"no-ylabel": "error"}
    assert config.per_tool["chartgx"]["ignore"] == ["no-ylabel"]
    (tmp_path / ".gxkit.toml").write_text('ignore = ["soft-lok"]\n', encoding="utf-8")
    assert load(tmp_path).ignore == {"soft-lok"}
