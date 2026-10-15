"""authzgx's domain knowledge: can a low-privilege principal reach something strong?

One directed graph — ``principal -> role -> (parent roles) -> permission`` — and
two questions: what can each principal reach, and can a *low* principal reach a
*sensitive* permission? The second is a privilege-escalation path, and it is
plain reachability plus `gxcore.graph.shortest_path`.
"""

from __future__ import annotations

from gxcore import ERROR, INFO, Problem, Report
from gxcore.graph import cycle_witnesses, reachable

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
        graph = model.graph()
        for principal in model.low:
            if principal not in declared_principals:
                continue
            reached = reachable(graph, [model.pid(principal)])
            for perm in model.sensitive:
                if model.xid(perm) in reached:
                    path = model.path(principal, perm)
                    shown = _arrow(model, path) if path else f"{principal} → {perm}"
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
                    report.details.append(
                        f"{principal} effective: "
                        + (", ".join(sorted(model.effective(principal))) or "none")
                    )
                    break

    reachable_all = model.reachable_from_principals()
    granted_perms = {perm for _, perm in model.grants}

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
        role_reached = reachable(model.graph(), [model.rid(role)])
        if not any(model.xid(x) in role_reached for x in model.permissions):
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
