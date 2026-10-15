"""Read the schema a project already has: SQL DDL.

A declaration is precise, but most databases already have a `.sql` file — a
schema dump, a migration, a fixture. Converting it costs nothing and changes no
claim: the converted schema is inspected by exactly the same checks as a
hand-written declaration, so a foreign-key cycle in a dump is the same defect as
one in a declaration.

Only the standard library reads the file, so an importer adds no runtime
dependency.

Two limits are deliberate rather than guessed at. A composite `PRIMARY KEY` or
`FOREIGN KEY` is refused: `Schema` records one primary key per table and one
column per foreign key, and silently picking one would let a check state
something untrue. Dialects differ in detail, so anything that is not a readable
`CREATE TABLE` is reported with its line rather than skipped.
"""

from __future__ import annotations

import re
from pathlib import Path

from gxcore.loading import InvalidArtifact

from .model import CONSTRAINT_WORDS, Schema, type_family

IDENTIFIER = r'"[^"]+"|`[^`]+`|\[[^\]]+\]|[\w$]+'
CREATE_TABLE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?P<name>" + IDENTIFIER + r")\s*\(",
    re.IGNORECASE,
)
OTHER_STATEMENT = re.compile(
    r"^\s*(CREATE|ALTER|DROP|INSERT|UPDATE|DELETE|COMMENT|GRANT|REVOKE|SET|BEGIN|TRUNCATE)\b",
    re.IGNORECASE,
)
REFERENCES = re.compile(
    r"REFERENCES\s+(?P<table>" + IDENTIFIER + r")\s*(?:\(\s*(?P<column>" + IDENTIFIER + r")\s*\))?",
    re.IGNORECASE,
)
PRIMARY_KEY = re.compile(r"^(?:CONSTRAINT\s+\S+\s+)?PRIMARY\s+KEY\s*\((?P<columns>[^)]*)\)", re.I)
FOREIGN_KEY = re.compile(
    r"^(?:CONSTRAINT\s+\S+\s+)?FOREIGN\s+KEY\s*\((?P<columns>[^)]*)\)\s*"
    r"REFERENCES\s+(?P<table>" + IDENTIFIER + r")\s*(?:\((?P<target>[^)]*)\))?",
    re.IGNORECASE,
)
TABLE_CONSTRAINT = re.compile(
    r"^(?:CONSTRAINT\b|PRIMARY\s+KEY\b|FOREIGN\s+KEY\b|UNIQUE\b|CHECK\b|EXCLUDE\b)",
    re.IGNORECASE,
)
COLUMN = re.compile(r"^(?P<name>" + IDENTIFIER + r")\s*(?P<rest>.*)$", re.DOTALL)


def _unquote(identifier: str) -> str:
    return identifier.strip().strip('"').strip("`").strip("[").strip("]").strip('"').strip()


def _without_comments(text: str) -> str:
    """Comments removed, newlines kept so a line number still means something."""
    return re.sub(r"--[^\n]*", "", re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL))


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _matching_paren(text: str, start: int) -> int:
    """The offset of the `)` matching the `(` at ``start``, outside string literals."""
    depth = 0
    quote = ""
    for index in range(start, len(text)):
        character = text[index]
        if quote:
            if character == quote:
                quote = ""
            continue
        if character in "'\"":
            quote = character
        elif character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                return index
    raise InvalidArtifact("a CREATE TABLE is never closed")


def _items(body: str, line: int, text: str, offset: int) -> list[tuple[int, str]]:
    """The top-level comma-separated items of a table body, with their lines."""
    items: list[tuple[int, str]] = []
    depth = 0
    quote = ""
    start = 0
    for index, character in enumerate(body):
        if quote:
            if character == quote:
                quote = ""
            continue
        if character in "'\"":
            quote = character
        elif character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
        elif character == "," and depth == 0:
            items.append((_line_of(text, offset + start), body[start:index].strip()))
            start = index + 1
    tail = body[start:].strip()
    if tail:
        items.append((_line_of(text, offset + start), tail))
    return [item for item in items if item[1]]


def _columns_of(text: str) -> list[str]:
    return [_unquote(name) for name in text.split(",") if name.strip()]


def _column_type(rest: str) -> str:
    """The declared type of a column, without its constraints."""
    taken: list[str] = []
    for word in rest.strip().split():
        if word.upper().strip("(),") in CONSTRAINT_WORDS:
            break
        taken.append(word)
        if len(taken) == 2 and " ".join(taken).lower() not in _MULTIWORD:
            # A multi-word type is only a type when the vocabulary knows it.
            break
    declared = " ".join(taken)
    if not declared:
        raise InvalidArtifact("a column declares no type")
    return declared


_MULTIWORD = {
    "character varying",
    "double precision",
    "timestamp with",
    "timestamp without",
    "time with",
    "time without",
    "bit varying",
}


def schema_from_ddl(text: str, *, source: str = "schema.sql") -> Schema:
    """A `Schema` from SQL DDL, or a rejection that names the offending line."""
    cleaned = _without_comments(text)
    tables: dict[str, dict[str, str]] = {}
    primary_keys: dict[str, str] = {}
    foreign_keys: list[tuple[str, str]] = []
    position = 0
    found = False
    while position < len(cleaned):
        match = CREATE_TABLE.search(cleaned, position)
        if match is None:
            remainder = cleaned[position:].strip()
            if remainder:
                line = _line_of(cleaned, position + len(cleaned[position:]) - len(remainder))
                if OTHER_STATEMENT.match(remainder):
                    raise InvalidArtifact(
                        f"{source}:{line}: only CREATE TABLE is read; "
                        "declare the schema in Python for anything else"
                    )
                raise InvalidArtifact(f"{source}:{line}: not a CREATE TABLE statement")
            break
        found = True
        table = _unquote(match.group("name"))
        if table in tables:
            raise InvalidArtifact(
                f"{source}:{_line_of(cleaned, match.start())}: table {table!r} is created twice"
            )
        open_paren = match.end() - 1
        close_paren = _matching_paren(cleaned, open_paren)
        body = cleaned[open_paren + 1 : close_paren]
        columns: dict[str, str] = {}
        for item_line, item in _items(body, 0, cleaned, open_paren + 1):
            if TABLE_CONSTRAINT.match(item):
                primary, foreign = _table_constraint(item, table, f"{source}:{item_line}")
                if primary is not None:
                    primary_keys[table] = primary
                if foreign is not None:
                    foreign_keys.append(foreign)
                continue
            column = COLUMN.match(item)
            if column is None:
                raise InvalidArtifact(f"{source}:{item_line}: not a column definition")
            name = _unquote(column.group("name"))
            if name in columns:
                raise InvalidArtifact(f"{source}:{item_line}: column {name!r} is declared twice")
            rest = column.group("rest")
            columns[name] = _column_type(rest)
            reference = REFERENCES.search(rest)
            if reference is not None:
                parent = _unquote(reference.group("table"))
                parent_column = _unquote(reference.group("column") or "id")
                foreign_keys.append((f"{table}.{name}", f"{parent}.{parent_column}"))
            if re.search(r"\bPRIMARY\s+KEY\b", rest, re.IGNORECASE):
                if table in primary_keys:
                    raise InvalidArtifact(
                        f"{source}:{item_line}: table {table!r} declares two primary keys"
                    )
                primary_keys[table] = name
        tables[table] = columns
        position = close_paren + 1
        while position < len(cleaned) and cleaned[position] in " \t\r\n":
            position += 1
        if position < len(cleaned) and cleaned[position] != ";":
            raise InvalidArtifact(
                f"{source}:{_line_of(cleaned, position)}: expected ';' after the table body"
            )
        position += 1
    if not found:
        raise InvalidArtifact(f"{source}: no CREATE TABLE statement")
    return Schema(
        tables=tables,
        primary_keys=primary_keys,
        foreign_keys=foreign_keys,
        name=Path(source).stem or "schema",
    )


def _table_constraint(
    item: str, table: str, where: str
) -> tuple[str | None, tuple[str, str] | None]:
    """(primary key column, foreign key pair) from a table-level constraint."""
    primary = PRIMARY_KEY.match(item)
    if primary is not None:
        columns = _columns_of(primary.group("columns"))
        if len(columns) != 1:
            raise InvalidArtifact(
                f"{where}: a composite primary key on {table!r} is not representable; "
                "declare the schema in Python"
            )
        return columns[0], None
    foreign = FOREIGN_KEY.match(item)
    if foreign is not None:
        columns = _columns_of(foreign.group("columns"))
        target = _columns_of(foreign.group("target") or "") or ["id"]
        if len(columns) != 1 or len(target) != 1:
            raise InvalidArtifact(
                f"{where}: a composite foreign key on {table!r} is not representable; "
                "declare the schema in Python"
            )
        parent = _unquote(foreign.group("table"))
        return None, (f"{table}.{columns[0]}", f"{parent}.{target[0]}")
    return None, None


def schema_from_file(path: str | Path) -> Schema:
    """A `Schema` from a SQL DDL file on disk."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InvalidArtifact(f"{path}: {exc}") from exc
    return schema_from_ddl(text, source=str(path))


__all__ = ["schema_from_ddl", "schema_from_file", "type_family"]
