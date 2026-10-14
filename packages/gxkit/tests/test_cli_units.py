"""gxkit's dispatcher branches the end-to-end tests do not reach."""

from __future__ import annotations

import pathlib

from gxkit import cli

ROOT = pathlib.Path(__file__).resolve().parents[3]


def test_tool_for_returns_none_for_an_unknown_explicit_tool(capsys):
    assert cli._tool_for(pathlib.Path("x.py"), "nope") is None
    assert "unknown tool" in capsys.readouterr().err


def test_tool_for_resolves_an_explicit_tool():
    assert cli._tool_for(pathlib.Path("x.py"), "levelgx").name == "levelgx"


def test_tool_for_reports_a_file_that_cannot_be_loaded(tmp_path, capsys):
    bad = tmp_path / "bad.py"
    bad.write_text("raise RuntimeError('boom')\n")
    assert cli._tool_for(bad, None) is None
    assert "RuntimeError" in capsys.readouterr().err


def test_codes_table_lists_one_tool_then_all_as_json(capsys):
    assert cli._codes_table(False, "levelgx") == 0
    assert "soft-lock" in capsys.readouterr().out
    assert cli._codes_table(True, None) == 0
    assert '"levelgx"' in capsys.readouterr().out
    assert cli._codes_table(False, "nope") == 2
    assert "unknown tool" in capsys.readouterr().err


def test_run_tool_forwards_the_flags(tmp_path, capsys):
    spec = cli.BY_NAME["levelgx"]
    good = ROOT / "packages" / "levelgx" / "examples" / "good_level.py"
    storyboard = tmp_path / "sb.png"
    args = cli.build_parser().parse_args(
        [
            "inspect",
            str(good),
            "-o",
            str(storyboard),
            "--json",
            "--no-storyboard",
            "--no-config",
        ]
    )
    assert cli._run_tool(spec, good, args) == 0
    captured = capsys.readouterr()
    assert "levelgx" in captured.err
    assert '"problems"' in captured.out


def test_codes_command_runs(capsys):
    assert cli.main(["codes", "levelgx"]) == 0
    assert "soft-lock" in capsys.readouterr().out
    assert cli.main(["codes"]) == 0
    assert "chartgx" in capsys.readouterr().out
    assert cli.main(["codes", "levelgx", "--json"]) == 0
    assert '"levelgx"' in capsys.readouterr().out


def test_main_reports_an_unexpected_error(monkeypatch, capsys):
    def boom(args):
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "_cmd_tools", boom)
    assert cli.main(["tools"]) == 2
    assert "RuntimeError" in capsys.readouterr().err


def test_inspect_forwards_a_baseline(tmp_path, capsys):
    good = ROOT / "packages" / "levelgx" / "examples" / "good_level.py"
    baseline = tmp_path / "b.json"
    assert (
        cli.main(["inspect", str(good), "--no-storyboard", "--write-baseline", str(baseline)]) == 0
    )
    capsys.readouterr()
    assert cli.main(["inspect", str(good), "--no-storyboard", "--baseline", str(baseline)]) == 0
    assert "baseline:" in capsys.readouterr().out


def test_a_baseline_with_two_files_is_refused(tmp_path, capsys):
    for name in ("a.py", "b.py"):
        (tmp_path / name).write_text("x = 1\n")
    baseline = tmp_path / "b.json"
    baseline.write_text('{"version": 1, "problems": []}')
    assert cli.main(["inspect", str(tmp_path), "--baseline", str(baseline)]) == 2
    assert "single artifact" in capsys.readouterr().err
