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


def test_path_gives_the_way_in():
    """The model's own answer to "how does this principal get there".

    The inspector asks it of the whole model at once (`gxcore.graph.route_to` +
    `route_nodes`, one traversal for every finding); this is the same walk for one
    principal and one permission.
    """
    assert GOOD.path("user", "read") == [
        "principal:user",
        "role:editor",
        "role:viewer",
        "perm:read",
    ]
    assert GOOD.path("user", "manage_users") is None


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


def test_a_role_that_inherits_itself_is_cyclic_too():
    """The one-node case of the same rule.

    Measured: `inherits=[("editor", "editor")]` reported no problem at all (exit 0)
    while the same cycle spread over two roles was an error, because the shared
    `cycle_witnesses` skipped size-one components.
    """
    m = AuthModel(roles=["editor"], permissions=["p"], inherits=[("editor", "editor")], name="x")
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


# --------------------------------------------------------------------------
# The cost of the questions, counted rather than timed.
#
# Measured before this: 2 000 principals took 5.8 s escalating and 1.8 s with a
# single finding, because every principal and every role cost its own traversal
# *and* a rebuild of the graph. A clock would make these flaky; the number of
# traversals is the thing that was wrong and it is exact.
# --------------------------------------------------------------------------


def _count_calls(monkeypatch, module, name, bucket, counts):
    """Wrap `module.name` so that each call adds one to `counts[bucket]`."""
    original = getattr(getattr(module, name), "_gxkit_real", getattr(module, name))

    def counting(*args, _real=original, **kwargs):
        counts[bucket] += 1
        return _real(*args, **kwargs)

    counting._gxkit_real = original  # type: ignore[attr-defined]
    monkeypatch.setattr(module, name, counting)


def _counting_inspection(monkeypatch, model):
    """Inspect `model` and report (traversals, walks, graph builds).

    A wrapper remembers the function it wrapped, so asking twice in one test counts
    from the real one instead of counting the first wrapper's calls into both sums.
    """
    import authzgx.authmodel as authmodel
    import authzgx.checks as checks

    counts = {"traversal": 0, "walk": 0, "graph": 0}
    for module in (checks, authmodel):
        _count_calls(monkeypatch, module, "route_nodes", "walk", counts)
        _count_calls(monkeypatch, module, "can_reach", "traversal", counts)
        _count_calls(monkeypatch, module, "route_to", "traversal", counts)
    # `reachable` is only bound in the model (the inspector asks one question, and
    # `reachable_from_principals` is what holds it).
    _count_calls(monkeypatch, authmodel, "reachable", "traversal", counts)
    original_graph = getattr(AuthModel.graph, "_gxkit_real", AuthModel.graph)

    def graph(self):
        counts["graph"] += 1
        return original_graph(self)

    graph._gxkit_real = original_graph  # type: ignore[attr-defined]
    monkeypatch.setattr(AuthModel, "graph", graph)
    inspect_auth(model)
    return counts


def _deep_model(principals, roles):
    """Every low principal escalates, through a chain of roles."""
    return AuthModel(
        principals=[f"p{i}" for i in range(principals)],
        roles=[f"r{i}" for i in range(roles)],
        permissions=["x0"],
        grants=[("r0", "x0")],
        inherits=[(f"r{i}", f"r{i - 1}") for i in range(1, roles)],
        assigned=[(f"p{i}", f"r{roles - 1}") for i in range(principals)],
        sensitive=["x0"],
        low=[f"p{i}" for i in range(principals)],
    )


def test_the_escalation_check_does_not_traverse_once_per_principal(monkeypatch):
    """Ten principals and two hundred cost the same traversals."""
    small = _counting_inspection(monkeypatch, _deep_model(10, 4))
    big = _counting_inspection(monkeypatch, _deep_model(200, 40))
    assert small["traversal"] == big["traversal"], (small, big)
    # One reverse traversal from the sensitive permissions, one route, the principal
    # set, and the roles' permission question — however many principals there are.
    assert big["traversal"] <= 6, big
    # The walk *is* proportional: one per finding, and it is the finding's own path.
    assert small["walk"] == 10 and big["walk"] == 200, (small, big)
    assert small["graph"] == 1 and big["graph"] == 1, (small, big)


def test_escalation_findings_are_proportional_to_the_report_not_the_model():
    """Two hundred escalating principals, one line each — the detail lines are the
    output, and they are the only thing that grows."""
    report = inspect_auth(_deep_model(200, 40))
    escalations = [p for p in report.problems if p.code == "escalation"]
    assert len(escalations) == 200
    assert len([d for d in report.details if " effective: " in d]) == 200


def test_effective_map_agrees_with_effective():
    """Two cost profiles, one rule: `effective` is one forward traversal for one
    principal, `effective_map` is one reverse traversal per permission for all of
    them. They must not be allowed to drift apart."""
    model = _deep_model(12, 5)
    model.grants.append(("r2", "x1"))
    model.permissions.append("x1")
    full = model.effective_map()
    assert set(full) == set(model.principals)
    for principal in model.principals:
        assert full[principal] == model.effective(principal), principal
    assert full["p0"] == {"x0", "x1"}
    # A subset is answered for the subset, and nobody else is built a set.
    assert set(model.effective_map(principals=["p0"])) == {"p0"}


def test_a_principal_that_does_not_escalate_is_never_given_a_route():
    """The route is asked for when a finding names the permission it leads to."""
    model = AuthModel(
        principals=["quiet", "loud"],
        roles=["none", "reader"],
        permissions=["read", "write"],
        grants=[("reader", "read")],
        assigned=[("quiet", "reader"), ("loud", "none")],
        sensitive=["read"],
        low=["loud"],
    )
    report = inspect_auth(model)
    assert_quiet(report, "escalation")
    assert not [d for d in report.details if " effective: " in d]


def test_the_escalation_message_shows_the_way_in():
    """The arrow is the grouped route, so it names the role that got there."""
    model = AuthModel(
        principals=["user"],
        roles=["editor"],
        permissions=["manage_users"],
        grants=[("editor", "manage_users")],
        assigned=[("user", "editor")],
        sensitive=["manage_users"],
        low=["user"],
    )
    report = inspect_auth(model)
    message = next(p.message for p in report.problems if p.code == "escalation")
    assert message.endswith("via user → editor → manage_users"), message
