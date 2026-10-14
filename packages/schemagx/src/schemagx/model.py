"""A relational schema, declared as data.

    import schemagx as s

    schema = s.Schema(
        tables={
            "users": {"id": "int", "email": "text"},
            "posts": {"id": "int", "author_id": "int", "title": "text"},
        },
        primary_keys={"users": "id", "posts": "id"},
        foreign_keys=[("posts.author_id", "users.id")],   # child -> parent
        roots=["users"],
    )

`foreign_keys` are ``"table.column"`` strings. Edges point from the referencing
(child) table to the referenced (parent) table, so a cycle is a real
foreign-key cycle and an unreferenced table is dead weight.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from gxcore.graph import find_cycle


@dataclass
class Schema:
    tables: dict[str, dict[str, str]] = field(default_factory=dict)
    primary_keys: dict[str, str] = field(default_factory=dict)
    foreign_keys: list[tuple[str, str]] = field(default_factory=list)
    roots: list[str] = field(default_factory=list)
    name: str = "schema"

    def table_names(self) -> list[str]:
        return list(self.tables)

    @staticmethod
    def split(reference: str) -> tuple[str, str]:
        table, _, column = reference.partition(".")
        return table, column

    def type_of(self, reference: str) -> str | None:
        table, column = self.split(reference)
        return self.tables.get(table, {}).get(column)

    def edges(self) -> dict[str, list[str]]:
        e: dict[str, list[str]] = {t: [] for t in self.tables}
        for child, parent in self.foreign_keys:
            ct, _ = self.split(child)
            pt, _ = self.split(parent)
            e.setdefault(ct, []).append(pt)
            e.setdefault(pt, [])
        return e

    def cycle(self) -> list[str] | None:
        # A table that references itself (manager_id -> users.id) is a tree, not
        # a cycle; only edges between distinct tables can form one.
        edges: dict[str, list[str]] = {t: [] for t in self.tables}
        for child, parent in self.foreign_keys:
            ct, _ = self.split(child)
            pt, _ = self.split(parent)
            if ct == pt:
                continue
            edges.setdefault(ct, []).append(pt)
            edges.setdefault(pt, [])
        return find_cycle(edges)

    def referenced_tables(self) -> set[str]:
        return {self.split(child)[0] for child, _ in self.foreign_keys} | {
            self.split(parent)[0] for _, parent in self.foreign_keys
        }


def _as_schema(value: object) -> "Schema | None":
    return value if isinstance(value, Schema) else None


def load_schema(path: str | Path) -> tuple[Schema, object]:
    from gxcore.loading import load_module, resolve

    path = Path(path)
    module = load_module(path)
    schema = resolve(
        module,
        attrs=("schema", "SCHEMA", "db", "model"),
        builders=("build", "make_schema", "make"),
        convert=_as_schema,
    )
    if schema is None:
        tables = getattr(module, "TABLES", getattr(module, "tables", None))
        if tables is not None:
            schema = Schema(
                tables={k: dict(v) for k, v in dict(tables).items()},
                primary_keys=dict(getattr(module, "PRIMARY_KEYS", getattr(module, "primary_keys", {}))),
                foreign_keys=[(f[0], f[1]) for f in getattr(module, "FOREIGN_KEYS", getattr(module, "foreign_keys", []))],
                roots=list(getattr(module, "ROOTS", getattr(module, "roots", []))),
            )
    if schema is None:
        raise ValueError(
            f"{path}: no schema found — define `schema` (a Schema) or "
            "TABLES/PRIMARY_KEYS/FOREIGN_KEYS"
        )
    if schema.name == "schema":
        schema.name = getattr(module, "NAME", path.stem)
    return schema, module


def schema_from_parts(
    tables: dict[str, dict[str, str]] | None = None,
    primary_keys: dict[str, str] | None = None,
    foreign_keys: list[tuple[str, str]] | None = None,
    roots: list[str] | None = None,
    name: str = "schema",
) -> Schema:
    return Schema(
        tables={k: dict(v) for k, v in (tables or {}).items()},
        primary_keys=dict(primary_keys or {}),
        foreign_keys=[(f[0], f[1]) for f in (foreign_keys or [])],
        roots=list(roots or []),
        name=name,
    )
