"""The code catalogue cannot drift: a source scan cross-checks every entry."""

from __future__ import annotations

import pathlib
import re

from gxkit.codes import CODEBOOK, flat, for_tool

PACKAGES = pathlib.Path(__file__).resolve().parents[2]
PROBLEM = re.compile(r'Problem\(\s*(ERROR|WARN|INFO)\s*,\s*"([a-z0-9-]+)"')


def _emitted() -> dict[str, set[str]]:
    seen: dict[str, set[str]] = {}
    for path in PACKAGES.rglob("*.py"):
        if {"tests", ".venv"} & set(path.parts):
            continue
        for match in PROBLEM.finditer(path.read_text(encoding="utf-8")):
            seen.setdefault(match.group(2), set()).add(match.group(1).lower())
    return seen


def test_catalogue_covers_every_emitted_code():
    known: dict[str, set[str]] = {}
    for codes in CODEBOOK.values():
        for code, severity in codes.items():
            known.setdefault(code, set()).add(severity)

    missing = sorted(
        (code, severity)
        for code, severities in _emitted().items()
        for severity in severities
        if code not in known or severity not in known[code]
    )
    assert not missing, f"codes emitted but not catalogued: {missing}"


def test_catalogue_has_no_stale_entries():
    emitted = {
        (code, severity) for code, severities in _emitted().items() for severity in severities
    }
    known = {(code, severity) for codes in CODEBOOK.values() for code, severity in codes.items()}
    stale = sorted(known - emitted)
    assert not stale, f"catalogued but never emitted: {stale}"


def test_for_tool_and_flat():
    assert for_tool("chartgx")["truncated-baseline"] == "error"
    assert "soft-lock" in for_tool("levelgx")
    assert for_tool("nope") == {}
    assert "chartgx" in flat()["truncated-baseline"]
    assert sorted(flat()["soft-lock"]) == ["levelgx"]
