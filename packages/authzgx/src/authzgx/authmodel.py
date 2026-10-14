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

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from gxcore.graph import reachable, shortest_path


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

    def effective(self, principal: str) -> set[str]:
        """Permission names a principal reaches."""
        from gxcore.graph import reachable as _reach

        reached = _reach(self.graph(), [self.pid(principal)])
        return {x for x in self.permissions if self.xid(x) in reached}

    def path(self, principal: str, permission: str) -> list[str] | None:
        return shortest_path(self.graph(), self.pid(principal), self.xid(permission))

    def labels(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for p in self.principals:
            out[self.pid(p)] = p
        for r in self.roles:
            out[self.rid(r)] = r
        for x in self.permissions:
            out[self.xid(x)] = x
        return out

    def reachable_from_principals(self) -> set[str]:
        all_nodes: set[str] = set()
        for p in self.principals:
            all_nodes |= reachable(self.graph(), [self.pid(p)])
        return all_nodes


def _as_model(value: object) -> "AuthModel | None":
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
                principals=list(getattr(module, "PRINCIPALS", getattr(module, "principals", []))),
                roles=list(getattr(module, "ROLES", getattr(module, "roles", []))),
                permissions=list(getattr(module, "PERMISSIONS", getattr(module, "permissions", []))),
                grants=[(g[0], g[1]) for g in grants],
                inherits=[(i[0], i[1]) for i in getattr(module, "INHERITS", getattr(module, "inherits", []))],
                assigned=[(a[0], a[1]) for a in getattr(module, "ASSIGNED", getattr(module, "assigned", []))],
                sensitive=list(getattr(module, "SENSITIVE", getattr(module, "sensitive", []))),
                low=list(getattr(module, "LOW", getattr(module, "low", []))),
            )
    if model is None:
        raise ValueError(
            f"{path}: no model found — define `model` (an AuthModel) or a "
            "GRANTS/ROLES/... set"
        )
    if model.name == "auth":
        model.name = getattr(module, "NAME", path.stem)
    return model, module


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
