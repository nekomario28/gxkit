"""authzgx's domain knowledge: can a low-privilege principal reach something strong?

One directed graph — ``principal -> role -> (parent roles) -> permission`` — and
two questions: what can each principal reach, and can a *low* principal reach a
*sensitive* permission? The second is a privilege-escalation path, and it is
plain reachability plus `gxcore.graph.shortest_path`.
"""

from __future__ import annotations

from gxcore import ERROR, INFO, Problem, Report
from gxcore.graph import can_reach, cycle_witnesses, route_nodes, route_to

from .authmodel import AuthModel
from .render import compute_layout, node_box


def _arrow(model: AuthModel, ids: list[str]) -> str:
    labels = model.labels()
    return " → ".join(labels.get(i, i.split(":", 1)[-1]) for i in ids)


def inspect_auth(model: AuthModel, name: str | None = None) -> Report:
    name = name or model.name
    declared_roles = set(model.roles)
    declared_perms = set(model.permissions)
    declared_principals = set(model.principals)

    report = Report(
        name=name,
        subject=f"auth: {len(model.principals)} principals, {len(model.roles)} roles, "
        f"{len(model.permissions)} permissions",
        details=[
            f"{len(model.principals)} principals, {len(model.roles)} roles, "
            f"{len(model.permissions)} permissions",
            "sensitive: " + (", ".join(model.sensitive) or "none"),
            "low: " + (", ".join(model.low) or "none"),
        ],
    )
    out: list[Problem] = []

    # references that name something undeclared
    # Each finding names a relationship and the side of it that does not resolve:
    # `(grant, role)` and `(grant, permission)` are different defects, and
    # replacing one unknown name with another is a new one.
    for role, perm in model.grants:
        if role not in declared_roles:
            out.append(
                Problem(
                    ERROR,
                    "dangling-grant",
                    f"grant names unknown role {role!r}",
                    identity=(f"grant:{role}:{perm}", "role", role),
                )
            )
        if perm not in declared_perms:
            out.append(
                Problem(
                    ERROR,
                    "dangling-grant",
                    f"grant names unknown permission {perm!r}",
                    identity=(f"grant:{role}:{perm}", "permission", perm),
                )
            )
    for principal, role in model.assigned:
        if principal not in declared_principals:
            out.append(
                Problem(
                    ERROR,
                    "dangling-assignment",
                    f"assignment names unknown principal {principal!r}",
                    identity=(f"assignment:{principal}:{role}", "principal", principal),
                )
            )
        if role not in declared_roles:
            out.append(
                Problem(
                    ERROR,
                    "dangling-assignment",
                    f"assignment names unknown role {role!r}",
                    identity=(f"assignment:{principal}:{role}", "role", role),
                )
            )
    for child, parent in model.inherits:
        for role in (child, parent):
            if role not in declared_roles:
                out.append(
                    Problem(
                        ERROR,
                        "dangling-inherit",
                        f"inheritance names unknown role {role!r}",
                        identity=(f"inherit:{child}:{parent}", role, role),
                    )
                )

    # role inheritance must be acyclic
    cycles = cycle_witnesses(model.role_edges())
    for witness, component in cycles:
        out.append(
            Problem(
                ERROR,
                "cyclic-inheritance",
                f"role inheritance is cyclic: {_arrow(model, witness)}",
                target=witness[0],
                identity=tuple(component),
            )
        )

    # A declared list this tool consumes must resolve. `low` and `sensitive` are
    # what the escalation check is *made of*: a typo'd name silently narrows the
    # search, so the answer "no escalation" would be about a different question.
    for field, names, known, what in (
        ("low", model.low, declared_principals, "principal"),
        ("sensitive", model.sensitive, set(model.permissions), "permission"),
    ):
        for name in names:
            if name not in known:
                out.append(
                    Problem(
                        ERROR,
                        "dangling-reference",
                        f"`{field}` names {name!r}, which is not a declared {what}",
                        # The relationship is (which list, which name): a different
                        # typo is a different defect.
                        identity=("dangling-reference", field, name),
                    )
                )

    # Every traversal below asks the *same* graph, so it is built once for the whole
    # inspection (it was built again inside each loop: with 2 000 roles the empty-role
    # scan alone spent 1.8 s rebuilding a graph it already had).
    graph = model.graph()

    # privilege escalation: a low principal reaches a sensitive permission
    if not model.sensitive:
        out.append(
            Problem(
                INFO,
                "no-sensitive",
                "no sensitive permissions declared, so escalation cannot be judged",
            )
        )
    elif not model.low:
        out.append(
            Problem(
                INFO,
                "no-low",
                "no low-privilege principals declared, so escalation cannot be judged",
            )
        )
    else:
        # "Does this principal escalate?" is one reverse traversal from all the
        # sensitive permissions at once. "Which permission is the one in the message,
        # and how does it get there?" is one reverse traversal *per sensitive
        # permission* — asked when a finding needs it and remembered, so a model whose
        # findings all land on the same permission pays for that one. The count of
        # traversals is bounded by the curated `sensitive` list and not by the number
        # of low principals: this used to be two traversals per low principal
        # (measured, 2 000 escalating principals: 5.8 s).
        reaches_sensitive = can_reach(graph, [model.xid(perm) for perm in model.sensitive])
        routes: dict[str, dict[str, str]] = {}

        def route(permission: str) -> dict[str, str]:
            found = routes.get(permission)
            if found is None:
                found = routes[permission] = route_to(graph, [model.xid(permission)])
            return found

        escalating = [
            p for p in model.low if p in declared_principals and model.pid(p) in reaches_sensitive
        ]
        # The detail line lists what each escalating principal is effective for. The
        # reverse form is one traversal per *permission* for all of them at once; the
        # forward form is one per escalating principal. Ask the cheaper question, so
        # neither a long inventory nor a long permission list is paid for twice.
        everything = (
            model.effective_map(graph, escalating)
            if len(escalating) > len(model.permissions)
            else None
        )

        for principal in escalating:
            pid = model.pid(principal)
            for perm in model.sensitive:
                hops = route(perm)
                if pid not in hops:
                    continue
                # `hops` has a route for `pid` — that is what `reaches_sensitive`
                # said — so the walk always lands on the permission named here.
                path = route_nodes(hops, pid)
                assert path is not None
                shown = _arrow(model, path)
                out.append(
                    Problem(
                        ERROR,
                        "escalation",
                        f"low principal {principal!r} reaches sensitive permission {perm!r} "
                        f"via {shown}",
                        target=model.xid(perm),
                        bbox=None,
                    )
                )
                effective = (
                    everything[principal]
                    if everything is not None
                    else model.effective(principal, graph)
                )
                report.details.append(
                    f"{principal} effective: " + (", ".join(sorted(effective)) or "none")
                )
                break

    reachable_all = model.reachable_from_principals(graph)
    granted_perms = {
        perm for _, perm in model.grants
    }  # "Which roles grant a permission, directly or by inheritance" is one reverse
    # traversal for all of them: a role is empty exactly when it cannot reach any
    # permission. Asked per role it was one fresh traversal — and one rebuilt graph —
    # for each role, which is what made this scan quadratic.
    reaches_a_permission = can_reach(graph, [model.xid(x) for x in model.permissions])

    for role in model.roles:
        if model.rid(role) not in reachable_all:
            out.append(
                Problem(
                    INFO,
                    "unreachable-role",
                    f"role {role!r} is not reachable from any principal",
                    target=model.rid(role),
                )
            )
        if model.rid(role) not in reaches_a_permission:
            out.append(
                Problem(
                    INFO,
                    "empty-role",
                    f"role {role!r} grants no permission (directly or by inheritance)",
                    target=model.rid(role),
                )
            )

    for perm in model.permissions:
        if perm not in granted_perms:
            out.append(
                Problem(
                    INFO,
                    "orphan-permission",
                    f"permission {perm!r} is not granted to any role",
                    target=model.xid(perm),
                )
            )
        elif model.xid(perm) not in reachable_all:
            out.append(
                Problem(
                    INFO,
                    "unreachable-permission",
                    f"permission {perm!r} cannot be reached by any principal",
                    target=model.xid(perm),
                )
            )

    if not model.roles:
        out.append(Problem(INFO, "no-permissions", "the model declares no roles"))

    positions, r = compute_layout(model)
    for p in out:
        if p.bbox is None and p.target in positions:
            p.bbox = node_box(positions[p.target], r)

    report.problems = out
    return report
