"""The identity debt is countable, and it may only shrink.

A finding with neither a `target` nor an `identity` is compared by its code alone,
so two of them in one artifact share a fingerprint and *replacing* one with another
reads as unchanged baseline debt. That is the class this repository has fixed
three times (a network edge endpoint, a cron conflict partner, an exposure route);
`docs/IDENTITY.md` lists what is left.

Two guards, in the same shape as the traceability document:

* the file must match the generator, so a new site cannot appear quietly;
* the count must not exceed the limit below, so growth needs a deliberate edit —
  fix a site and lower the limit, and never raise it without saying why.
"""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DOCUMENT = ROOT / "docs" / "IDENTITY.md"

#: Lower this as sites are fixed. Raising it needs a reason in the commit message.
IDENTITY_DEBT_LIMIT = 24


def _script() -> dict:
    return runpy.run_path(str(ROOT / "scripts" / "make_identity.py"))


def test_the_identity_document_is_current():
    generated = _script()["build"]()
    assert DOCUMENT.read_text(encoding="utf-8") == generated, (
        "docs/IDENTITY.md is stale; run `python scripts/make_identity.py` and read the diff"
    )


def test_the_identity_debt_only_shrinks():
    found = _script()["sites"]()
    total = sum(len(codes) for codes in found.values())
    assert total <= IDENTITY_DEBT_LIMIT, (
        f"{total} error findings cannot be told apart, above the limit of "
        f"{IDENTITY_DEBT_LIMIT}. Give the new finding a target or a relationship "
        f"identity, or raise the limit deliberately and say why."
    )


def test_a_finding_that_cannot_be_told_apart_is_what_the_document_is_about():
    """The property, on a real artifact: two routes, two fingerprints.

    This is the fix `netgx` needed — the check reported the first public entry and
    identified the finding by the sensitive node, so a changed route was invisible.
    """
    from gxcore.baseline import fingerprint
    from netgx import Network, inspect_network

    net = Network(
        nodes={"a": "public", "b": "public", "db": "data"},
        edges=[("a", "db"), ("b", "db")],
        sensitive=["db"],
    )
    found = [p for p in inspect_network(net).problems if p.code == "public-reaches-sensitive"]
    assert len(found) == 2
    keys = {fingerprint(p.code, p.target, p.label, p.identity) for p in found}
    assert len(keys) == 2, "two exposure routes share a fingerprint"


@pytest.mark.parametrize("tool", ["authzgx", "framegx", "protogx", "shadergx"])
def test_a_listed_site_is_listed_because_it_carries_neither(tool):
    """The document is not a guess: the listed codes really have neither field.

    Checked against the parsed source rather than the rendered table, so a tool
    that gains a target or an identity leaves the list on the next generation.
    """
    import ast

    listed = _script()["sites"]()
    assert listed.get(tool), f"{tool} is not in the inventory; the list changed"
    for path in sorted((ROOT / "packages").glob(f"{tool}/src/{tool}/*.py")):
        for node in ast.walk(ast.parse(path.read_bytes(), filename=str(path))):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", "") or getattr(node.func, "id", "")
            if name not in {"Problem", "_problem"}:
                continue
            args = node.args
            if not args or not isinstance(args[0], ast.Name) or args[0].id != "ERROR":
                continue
            if len(args) < 2 or not isinstance(args[1], ast.Constant):
                continue
            keywords = {keyword.arg for keyword in node.keywords}
            if {"identity", "target"} & keywords:
                continue
            assert str(args[1].value) in listed[tool]
