"""A permission model: principals, roles, permissions, and how they connect.

    import authzgx as a

    model = a.AuthModel(
        principals=["anonymous", "user", "admin"],
        roles=["viewer", "editor", "owner"],
        permissions=["read", "write", "delete", "manage_users"],
        grants=[("viewer", "read"), ("editor", "write"), ("owner", "delete"),
                ("editor", "manage_users")],
        inherits=[("editor", "viewer"), ("owner", "editor")],   # child gets parent's perms
        assigned=[("user", "editor"), ("admin", "owner")],
        sensitive=["delete", "manage_users"],
        low=["anonymous", "user"],
    )

A principal *reaches* a permission when it is assigned a role that grants the
permission or inherits (transitively) from one that does. That is a reachability
question on one directed graph, which `gxcore.graph` answers — and a low
principal reaching a sensitive permission is a privilege-escalation path.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from gxcore.graph import can_reach, reachable, route_nodes, route_to
from gxcore.loading import convert_names, convert_pairs, validate_names, validate_pairs


@dataclass
class AuthModel:
    principals: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    grants: list[tuple[str, str]] = field(default_factory=list)
    inherits: list[tuple[str, str]] = field(default_factory=list)
    assigned: list[tuple[str, str]] = field(default_factory=list)
    sensitive: list[str] = field(default_factory=list)
    low: list[str] = field(default_factory=list)
    name: str = "auth"

    # -- node ids: a principal, role and permission may share a name ---------- #

    def pid(self, p: str) -> str:
        return f"principal:{p}"

    def rid(self, r: str) -> str:
        return f"role:{r}"

    def xid(self, x: str) -> str:
        return f"perm:{x}"

    def all_nodes(self) -> list[str]:
        ids: list[str] = []
        for p in self.principals:
            ids.append(self.pid(p))
        for r in self.roles:
            ids.append(self.rid(r))
        for x in self.permissions:
            ids.append(self.xid(x))
        return ids

    def graph(self) -> dict[str, list[str]]:
        """principal -> role -> (parent roles) -> permissions."""
        edges: dict[str, list[str]] = {nid: [] for nid in self.all_nodes()}
        for p, r in self.assigned:
            edges.setdefault(self.pid(p), []).append(self.rid(r))
            edges.setdefault(self.rid(r), [])
        for child, parent in self.inherits:
            edges.setdefault(self.rid(child), []).append(self.rid(parent))
            edges.setdefault(self.rid(parent), [])
        for role, perm in self.grants:
            edges.setdefault(self.rid(role), []).append(self.xid(perm))
            edges.setdefault(self.xid(perm), [])
        return edges

    def role_edges(self) -> dict[str, list[str]]:
        edges: dict[str, list[str]] = {self.rid(r): [] for r in self.roles}
        for child, parent in self.inherits:
            edges.setdefault(self.rid(child), []).append(self.rid(parent))
            edges.setdefault(self.rid(parent), [])
        return edges

    def effective(self, principal: str, graph: dict[str, list[str]] | None = None) -> set[str]:
        """Permission names a principal reaches. One forward traversal.

        ``graph`` is the option to hand over a graph you already built: the
        inspector asks one question at a time and must not rebuild it.
        """
        reached = reachable(self.graph() if graph is None else graph, [self.pid(principal)])
        return {x for x in self.permissions if self.xid(x) in reached}

    def effective_map(
        self,
        graph: dict[str, list[str]] | None = None,
        principals: Iterable[str] | None = None,
    ) -> dict[str, set[str]]:
        """Permission names each of ``principals`` (default: every principal) reaches.

        `effective` answers the question for one principal with one forward
        traversal, so asking it of every principal costs a traversal each. Asking
        it backwards — *which nodes reach this permission* — answers all of them at
        once, at one traversal per permission; the cost then depends on the
        declared permission set rather than on how many principals the inventory
        happens to list.

        ``principals`` narrows the answer to the ones actually asked about: a
        caller that needs it for a handful of them must not pay a set lookup for
        every (principal, permission) pair in the model.

        The two forms must agree; `test_effective_map_agrees_with_effective` pins it.
        """
        edges = self.graph() if graph is None else graph
        wanted = list(self.principals if principals is None else principals)
        reaching = {x: can_reach(edges, [self.xid(x)]) for x in self.permissions}
        out: dict[str, set[str]] = {}
        for p in wanted:
            pid = self.pid(p)
            out[p] = {x for x in self.permissions if pid in reaching[x]}
        return out

    def path(
        self,
        principal: str,
        permission: str,
        graph: dict[str, list[str]] | None = None,
    ) -> list[str] | None:
        edges = self.graph() if graph is None else graph
        return route_nodes(route_to(edges, [self.xid(permission)]), self.pid(principal))

    def labels(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for p in self.principals:
            out[self.pid(p)] = p
        for r in self.roles:
            out[self.rid(r)] = r
        for x in self.permissions:
            out[self.xid(x)] = x
        return out

    def reachable_from_principals(self, graph: dict[str, list[str]] | None = None) -> set[str]:
        """Everything any principal reaches, in one traversal.

        The union of the reachable sets from the principals is the reachable set
        from all of them at once, so this was one traversal per principal for a
        result one traversal gives (measured: 2 000 principals spent 1.8 s here).
        """
        edges = self.graph() if graph is None else graph
        return reachable(edges, [self.pid(p) for p in self.principals])

    def __post_init__(self) -> None:
        validate_names(self.principals, field="principals")
        validate_names(self.roles, field="roles")
        validate_names(self.permissions, field="permissions")
        validate_names(self.sensitive, field="sensitive")
        validate_names(self.low, field="low")
        validate_pairs(self.grants, field="grants", arity=2)
        validate_pairs(self.inherits, field="inherits", arity=2)
        validate_pairs(self.assigned, field="assigned", arity=2)


def _as_model(value: object) -> AuthModel | None:
    return value if isinstance(value, AuthModel) else None


def load_model(path: str | Path) -> tuple[AuthModel, object]:
    from gxcore.loading import load_module, resolve

    path = Path(path)
    module = load_module(path)
    model = resolve(
        module,
        attrs=("model", "AUTH", "auth", "MODEL"),
        builders=("build", "make_model", "make"),
        convert=_as_model,
    )
    if model is None:
        grants = getattr(module, "GRANTS", getattr(module, "grants", None))
        if grants is not None:
            model = AuthModel(
                principals=_names(
                    getattr(module, "PRINCIPALS", getattr(module, "principals", [])), "PRINCIPALS"
                ),
                roles=_names(getattr(module, "ROLES", getattr(module, "roles", [])), "ROLES"),
                permissions=_names(
                    getattr(module, "PERMISSIONS", getattr(module, "permissions", [])),
                    "PERMISSIONS",
                ),
                grants=convert_pairs(grants, field="GRANTS", arity=2),
                inherits=convert_pairs(
                    getattr(module, "INHERITS", getattr(module, "inherits", [])),
                    field="INHERITS",
                    arity=2,
                ),
                assigned=convert_pairs(
                    getattr(module, "ASSIGNED", getattr(module, "assigned", [])),
                    field="ASSIGNED",
                    arity=2,
                ),
                sensitive=_names(
                    getattr(module, "SENSITIVE", getattr(module, "sensitive", [])), "SENSITIVE"
                ),
                low=_names(getattr(module, "LOW", getattr(module, "low", [])), "LOW"),
            )
    if model is None:
        raise ValueError(
            f"{path}: no model found — define `model` (an AuthModel) or a GRANTS/ROLES/... set"
        )
    if model.name == "auth":
        model.name = getattr(module, "NAME", path.stem)
    return model, module


def _names(value: object, field: str) -> list[str]:
    """A declared name list, or a located refusal.

    `GRANTS = ["rp"]` was read as a role→permission grant of the characters `r` and
    `p`: a string inside a list of pairs invented permissions the declaration never
    named.
    """
    return convert_names(value, field=field)


def auth_from_parts(
    principals: Iterable[str] | None = None,
    roles: Iterable[str] | None = None,
    permissions: Iterable[str] | None = None,
    grants: Iterable[tuple[str, str]] | None = None,
    inherits: Iterable[tuple[str, str]] | None = None,
    assigned: Iterable[tuple[str, str]] | None = None,
    sensitive: Iterable[str] | None = None,
    low: Iterable[str] | None = None,
    name: str = "auth",
) -> AuthModel:
    return AuthModel(
        principals=list(principals or []),
        roles=list(roles or []),
        permissions=list(permissions or []),
        grants=[(g[0], g[1]) for g in (grants or [])],
        inherits=[(i[0], i[1]) for i in (inherits or [])],
        assigned=[(a[0], a[1]) for a in (assigned or [])],
        sensitive=list(sensitive or []),
        low=list(low or []),
        name=name,
    )
