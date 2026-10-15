"""A malformed member must not disappear before the public inspector sees it."""

from __future__ import annotations

import pytest
from gxkit.cli import main


@pytest.mark.parametrize(
    ("tool", "source"),
    [
        ("crongx", 'RUNS = [("ok", 0, 10), 42]\n'),
        ("seedgx", 'STREAMS = [("ok", 1), 42]\n'),
        ("pipegx", 'STEPS = [("ok", []), 42]\n'),
        ("seedgx", 'spec = {"streams": [("ok",1),42]}\nSTREAMS = [("fallback",1)]\n'),
        ("seedgx", 'from seedgx import SeedSpec\nspec = SeedSpec(["ok",42])\n'),
        ("crongx", 'schedule = {"runs": [("ok",0,10),42]}\n'),
        ("pipegx", 'pipeline = [("ok", []),42]\n'),
        ("envgx", 'env = {"variables": ["ok", 42], "references": ["ok"]}\n'),
        (
            "apigx",
            'api = {"endpoints": [{"method":"GET","path":"/v1/a","statuses":[200,404]}, 42]}\n',
        ),
    ],
)
def test_malformed_members_are_rejected_with_their_index(tmp_path, capsys, tool, source):
    path = tmp_path / "artifact.py"
    path.write_text(source, encoding="utf-8")
    assert main(["inspect", tool, str(path), "--no-storyboard", "--no-config"]) == 2
    err = capsys.readouterr().err
    assert "[1]" in err and "Traceback" not in err


@pytest.mark.parametrize(
    ("tool", "parent", "fallback"),
    [
        (
            "envgx",
            'env = {"variables": ["TOKEN"], "references": None}\n',
            'VARIABLES = {"PORT": "int"}\nREFERENCES = ["PORT"]\n',
        ),
        ("pipegx", 'pipeline = {"steps": ["build"], "goals": None}\n', 'STEPS = ["build"]\n'),
        (
            "apigx",
            'api = {"endpoints": [{"method":"POST","path":"/v1/mutate","auth":False,"statuses":[201,400]}], "auth_schemes": None}\n',
            'ENDPOINTS = ["GET /v1/ok"]\n',
        ),
    ],
)
def test_a_recognized_parent_with_an_invalid_collection_is_not_replaced(
    tmp_path, capsys, tool, parent, fallback
):
    """A recognized shape must fail closed, even when a clean one is declared beside it."""
    path = tmp_path / "artifact.py"
    path.write_text(parent + fallback, encoding="utf-8")
    assert main(["inspect", tool, str(path), "--no-storyboard", "--no-config"]) == 2
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert fallback.split(" =")[0] not in err


@pytest.mark.parametrize(
    ("tool", "parent", "expected"),
    [
        ("envgx", 'env = {"variables": ["TOKEN"], "references": ["PORT"]}\n', 1),
        ("pipegx", 'pipeline = {"steps": ["build"], "goals": ["app"]}\n', 1),
        (
            "apigx",
            'api = {"endpoints": [{"method":"POST","path":"/v1/mutate","auth":False,"statuses":[201,400]}], "auth_schemes": []}\n',
            1,
        ),
    ],
)
def test_a_recognized_parent_with_valid_collections_keeps_its_findings(
    tmp_path, tool, parent, expected
):
    path = tmp_path / "artifact.py"
    path.write_text(parent, encoding="utf-8")
    assert main(["inspect", tool, str(path), "--no-storyboard", "--no-config"]) == expected


@pytest.mark.parametrize(
    ("tool", "source", "index"),
    [
        ("envgx", 'env = {"variables": ["TOKEN"], "references": ["PORT", 42]}\n', "references[1]"),
        ("pipegx", 'pipeline = {"steps": ["build"], "goals": [42]}\n', "goals[0]"),
        ("apigx", 'api = {"endpoints": ["GET /v1/a"], "auth_schemes": [42]}\n', "auth_schemes[0]"),
    ],
)
def test_a_malformed_name_reports_its_field_and_index(tmp_path, capsys, tool, source, index):
    path = tmp_path / "artifact.py"
    path.write_text(source, encoding="utf-8")
    assert main(["inspect", tool, str(path), "--no-storyboard", "--no-config"]) == 2
    assert index in capsys.readouterr().err
