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

#: No finding that can occur twice in one artifact may be indistinguishable from a
#: sibling. Raising this needs a reason in the commit message.
IDENTITY_DEBT_LIMIT = 0


def _script() -> dict:
    return runpy.run_path(str(ROOT / "scripts" / "make_identity.py"))


def test_the_identity_document_is_current():
    generated = _script()["build"]()
    assert DOCUMENT.read_text(encoding="utf-8") == generated, (
        "docs/IDENTITY.md is stale; run `python scripts/make_identity.py` and read the diff"
    )


def test_no_finding_that_can_repeat_is_indistinguishable():
    owing = _script()["debt"]()
    total = sum(len(codes) for codes in owing.values())
    assert total <= IDENTITY_DEBT_LIMIT, (
        f"{total} error findings can occur twice and cannot be told apart, above the "
        f"limit of {IDENTITY_DEBT_LIMIT}: {owing}. Give the finding a target or a "
        f"relationship identity, or raise the limit deliberately and say why."
    )


def test_every_justified_site_is_still_a_site():
    """The reasons cannot go stale: a site that gains a location leaves the table."""
    found = _script()["sites"]()
    justified = _script()["UNIQUE_PER_ARTIFACT"]
    for (tool, code), reason in justified.items():
        assert code in found.get(tool, []), (
            f"{tool}.{code} is justified as once-per-artifact ({reason!r}) and no "
            f"longer needs the entry; remove it"
        )


def test_a_justification_is_a_reason_not_a_label():
    """Each entry names the guard in the source that makes it unique."""
    for (tool, code), reason in _script()["UNIQUE_PER_ARTIFACT"].items():
        assert len(reason) > 20, f"{tool}.{code}: {reason!r} is not a reason"
        assert "one" in reason or "single" in reason, f"{tool}.{code}: {reason!r}"


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


@pytest.mark.parametrize(
    ("tool", "code"),
    [
        ("flowgx", "no-start"),
        ("framegx", "frozen"),
        ("protogx", "unhandled-message"),
        ("schemagx", "dangling-foreign-key"),
    ],
)
def test_the_source_really_has_no_location_for_that_finding(tool, code):
    """The premise of the whole document, checked against the parsed source.

    `framegx.frozen` is a *justified* site (it carries a `label`, so it is
    distinguishable and not listed); `protogx.unhandled-message` and
    `schemagx.dangling-foreign-key` carry an identity now. Each entry asserts what
    the judgement rests on rather than trusting the rendered table.
    """
    import ast

    script = _script()
    listed = script["sites"]()
    occurrences = 0
    for path in sorted((ROOT / "packages").glob(f"{tool}/src/{tool}/*.py")):
        for node in ast.walk(ast.parse(path.read_bytes(), filename=str(path))):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", "") or getattr(node.func, "id", "")
            if name not in {"Problem", "_problem"}:
                continue
            args = node.args
            if len(args) < 2 or not isinstance(args[1], ast.Constant):
                continue
            if str(args[1].value) != code:
                continue
            occurrences += 1
            keywords = {keyword.arg for keyword in node.keywords}
            distinguishable = bool({"identity", "target", "label"} & keywords)
            if (tool, code) in script["UNIQUE_PER_ARTIFACT"]:
                assert not distinguishable, f"{tool}.{code} now has a location; drop the entry"
            if not distinguishable:
                assert code in listed.get(tool, []), f"{tool}.{code} is a site and not listed"
    assert occurrences, f"{tool}.{code} is not in the source at all"
