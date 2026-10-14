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
