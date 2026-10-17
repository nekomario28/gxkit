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

import re
from dataclasses import dataclass, field
from pathlib import Path

CONSTRAINT_WORDS = (
    "PRIMARY",
    "NOT",
    "NULL",
    "UNIQUE",
    "DEFAULT",
    "REFERENCES",
    "CHECK",
    "GENERATED",
    "CONSTRAINT",
    "COLLATE",
    "AUTO_INCREMENT",
    "AUTOINCREMENT",
    # Modifiers that follow a type; they are not part of it.
    "UNSIGNED",
    "ZEROFILL",
)

# Unambiguous synonyms, so a PostgreSQL schema is not reported as a type
# mismatch on every key. Length and precision are dropped: a `VARCHAR(50)`
# column referencing a `VARCHAR(255)` one is normal and not a defect.
TYPE_FAMILIES = {
    "int": "int",
    "integer": "int",
    "int4": "int",
    "serial": "int",
    "serial4": "int",
    "smallint": "smallint",
    "int2": "smallint",
    "smallserial": "smallint",
    "serial2": "smallint",
    "bigint": "bigint",
    "int8": "bigint",
    "bigserial": "bigint",
    "serial8": "bigint",
    "bool": "bool",
    "boolean": "bool",
    "text": "text",
    "varchar": "varchar",
    "character varying": "varchar",
    "char": "char",
    "character": "char",
    "bpchar": "char",
    "uuid": "uuid",
    "timestamp": "timestamp",
    "timestamptz": "timestamp",
    "timestamp with time zone": "timestamp",
    "timestamp without time zone": "timestamp",
    "datetime": "timestamp",
    "date": "date",
    "time": "time",
    "timetz": "time",
    "time with time zone": "time",
    "float": "float",
    "float4": "float",
    "real": "float",
    "float8": "double",
    "double precision": "double",
    "double": "double",
    "numeric": "numeric",
    "decimal": "numeric",
    "money": "numeric",
    "json": "json",
    "jsonb": "jsonb",
    "bytea": "bytea",
    "blob": "bytea",
}


@dataclass
class Schema:
    tables: dict[str, dict[str, str]] = field(default_factory=dict)
    primary_keys: dict[str, str] = field(default_factory=dict)
    foreign_keys: list[tuple[str, str]] = field(default_factory=list)
    roots: list[str] = field(default_factory=list)
    #: Clauses a *reader* saw and this model does not carry, as `(table, kinds)`.
    #: The model is about reference integrity, so `NOT NULL`, `DEFAULT`, `UNIQUE`
    #: and the rest are not represented — but they are reported, because a reader
    #: that drops what it read and then says "clean" is the silence this family
    #: refuses. Hand-written schemas leave it empty.
    not_modelled: list[tuple[str, str]] = field(default_factory=list)
    #: Whether `roots` means anything for this schema. A reader that cannot express
    #: entry points (the SQL importer: DDL has no such declaration) leaves it False,
    #: which is what tells the rules *roots* decides — `orphan-table` among them —
    #: not to apply. Measured: without it the same schema gained
    #: `orphan-table: nothing references 'users'` on the SQL route and was clean on
    #: the Python one.
    roots_modelled: bool = True
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

    def referenced_tables(self) -> set[str]:
        return {self.split(child)[0] for child, _ in self.foreign_keys} | {
            self.split(parent)[0] for _, parent in self.foreign_keys
        }


def type_family(declared: str) -> str:
    """The comparable family of a declared column type."""
    text = declared.strip().lower()
    text = re.sub(r"\s*\([^)]*\)", "", text).strip()
    for suffix in (" unsigned", " zerofill"):
        text = text.removesuffix(suffix).strip()
    return TYPE_FAMILIES.get(text, text)


def _as_schema(value: object) -> Schema | None:
    return value if isinstance(value, Schema) else None


def load_schema(path: str | Path) -> tuple[Schema, object]:
    # A SQL file is the schema most databases already have; a `.sql` path is
    # read as DDL rather than executed as Python.
    if Path(path).suffix.lower() == ".sql":
        from .ddl import schema_from_file

        return schema_from_file(path), path

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
                primary_keys=dict(
                    getattr(module, "PRIMARY_KEYS", getattr(module, "primary_keys", {}))
                ),
                foreign_keys=[
                    (f[0], f[1])
                    for f in getattr(module, "FOREIGN_KEYS", getattr(module, "foreign_keys", []))
                ],
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
