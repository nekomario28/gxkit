"""Prove every authzgx check fires on a model that has the fault.

The headline case — a low principal reaching a sensitive permission — is a
path found with `gxcore.graph`, not a heuristic.
"""

from __future__ import annotations

from pathlib import Path

from authzgx import AuthModel, inspect_auth, load_model
from gxcore import ERROR, INFO
from gxcore.testing import assert_fires, assert_quiet

GOOD = AuthModel(
    principals=["anonymous", "user", "admin"],
    roles=["viewer", "editor", "owner"],
    permissions=["read", "write", "delete", "manage_users"],
    grants=[
        ("viewer", "read"),
        ("editor", "write"),
        ("owner", "delete"),
        ("owner", "manage_users"),
    ],
    inherits=[("editor", "viewer"), ("owner", "editor")],
    assigned=[("user", "editor"), ("admin", "owner")],
    sensitive=["delete", "manage_users"],
    low=["anonymous", "user"],
    name="good",
)


def test_good_model_has_no_errors():
    r = inspect_auth(GOOD)
    assert r.errors == 0


def test_effective_permissions_use_inheritance():
    assert GOOD.effective("user") == {"read", "write"}
    assert GOOD.effective("admin") == {"read", "write", "delete", "manage_users"}
    assert GOOD.effective("anonymous") == set()


def test_escalation_fires_with_a_path():
    leaky = AuthModel(
        principals=["user"],
        roles=["editor"],
        permissions=["manage_users"],
        grants=[("editor", "manage_users")],
        assigned=[("user", "editor")],
        sensitive=["manage_users"],
        low=["user"],
        name="leak",
    )
    r = inspect_auth(leaky)
    assert_fires(r, "escalation", ERROR)
    msg = next(p.message for p in r.problems if p.code == "escalation")
    assert "user" in msg and "manage_users" in msg and "→" in msg


def test_no_escalation_when_low_does_not_reach():
    assert_quiet(inspect_auth(GOOD), "escalation")


def test_dangling_grant():
    m = AuthModel(roles=["r"], permissions=["p"], grants=[("ghost", "p")], name="x")
    assert_fires(inspect_auth(m), "dangling-grant", ERROR)


def test_dangling_assignment():
    m = AuthModel(principals=["p"], roles=["r"], assigned=[("p", "ghost")], name="x")
    assert_fires(inspect_auth(m), "dangling-assignment", ERROR)


def test_cyclic_inheritance():
    m = AuthModel(roles=["a", "b"], permissions=["p"], inherits=[("a", "b"), ("b", "a")], name="x")
    assert_fires(inspect_auth(m), "cyclic-inheritance", ERROR)


def test_unreachable_role_and_orphan_permission():
    m = AuthModel(
        principals=["p"],
        roles=["r", "ghost"],
        permissions=["unused"],
        assigned=[("p", "r")],
        name="x",
    )
    r = inspect_auth(m)
    assert_fires(r, "unreachable-role", INFO)
    assert_fires(r, "orphan-permission", INFO)


def test_examples_load_and_are_diagnosed():
    examples = Path(__file__).resolve().parents[1] / "examples"
    good, _ = load_model(examples / "good_auth.py")
    leaky, _ = load_model(examples / "escalate_auth.py")
    assert inspect_auth(good).errors == 0
    r = inspect_auth(leaky)
    assert_fires(r, "escalation", ERROR)
    assert_fires(r, "dangling-grant", ERROR)
    assert_fires(r, "unreachable-role", INFO)
    assert_fires(r, "orphan-permission", INFO)


def test_a_declared_list_that_names_nothing_is_reported():
    """`low` and `sensitive` are what the escalation check is made of.

    Measured before: a typo'd `low` was skipped (`if principal not in
    declared_principals: continue`) and `inspect` said nothing at all, so the
    answer "no escalation" was about a question nobody asked.
    """
    base = dict(
        principals=["u"],
        roles=["r1"],
        permissions=["secret"],
        grants=[("r1", "secret")],
        assigned=[("u", "r1")],
        sensitive=["secret"],
        low=["u"],
    )
    report = inspect_auth(AuthModel(**base))
    assert_fires(report, "escalation", ERROR)

    for field, value in (("low", ["ghost"]), ("sensitive", ["ghost"])):
        report = inspect_auth(AuthModel(**(base | {field: value})))
        assert_fires(report, "dangling-reference", ERROR), field
        assert [p.code for p in report.problems if p.severity == ERROR] == ["dangling-reference"]
        assert field in report.problems[0].message

    # A role is not a principal, and saying so is the finding.
    report = inspect_auth(AuthModel(**(base | {"low": ["r1"]})))
    assert_fires(report, "dangling-reference", ERROR)
    assert "not a declared principal" in report.problems[0].message
