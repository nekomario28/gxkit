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
_CONSTRAINT_NAME = r"CONSTRAINT\s+(?:" + IDENTIFIER + r")\s+"
PRIMARY_KEY = re.compile(
    r"^(?:" + _CONSTRAINT_NAME + r")?PRIMARY\s+KEY\s*\((?P<columns>[^)]*)\)", re.I
)
FOREIGN_KEY = re.compile(
    r"^(?:" + _CONSTRAINT_NAME + r")?FOREIGN\s+KEY\s*\((?P<columns>[^)]*)\)\s*"
    r"REFERENCES\s+(?P<table>" + IDENTIFIER + r")\s*(?:\((?P<target>[^)]*)\))?",
    re.IGNORECASE,
)
#: Clauses inside `CREATE TABLE` that this model has no place for. Recognised so
#: they can be *reported*; a statement outside `CREATE TABLE` is refused outright.
NOT_MODELLED = re.compile(
    r"\b(NOT\s+NULL|DEFAULT|UNIQUE|CHECK|EXCLUDE|AUTOINCREMENT|AUTO_INCREMENT|"
    r"COLLATE|GENERATED|ON\s+DELETE|ON\s+UPDATE|ON\s+CONFLICT"
    r"|AUTO_INCREMENT\s*=|COLLATE)\b",
    re.IGNORECASE,
)
#: Index clauses are matched by `INDEX_CLAUSE` first, which requires the name and the
#: column list: adding a bare `KEY`/`INDEX` alternative here made a *column* named
#: `key` a constraint and dropped it (measured: a column-level PRIMARY KEY vanished).
TABLE_CONSTRAINT = re.compile(
    r"^(?:CONSTRAINT\b|PRIMARY\s+KEY\b|FOREIGN\s+KEY\b|UNIQUE\b|CHECK\b|EXCLUDE\b)",
    re.IGNORECASE,
)
#: An index definition is a table-level clause the model has no place for — and
#: reading `KEY idx_email (email)` as a column named `KEY` invented one (measured).
INDEX_CLAUSE = re.compile(
    r"^(?:CONSTRAINT\s+(?:" + IDENTIFIER + r")\s+)?"
    r"(?:UNIQUE\s+|FULLTEXT\s+|SPATIAL\s+)?(?:KEY|INDEX)\s+(?:" + IDENTIFIER + r")\s*\(",
    re.IGNORECASE,
)
#: Table options that follow the closing parenthesis. They are SQL (not another
#: statement), so a dump that has them is readable — reported, not refused.
#: No leading `^`: this is matched at an offset with `Pattern.match(text, pos)`, and
#: `^` would still require the start of the whole document.
TABLE_OPTIONS = re.compile(
    r"(?:WITHOUT\s+ROWID|STRICT|ENGINE\s*=\s*\w+|DEFAULT\s+(?:CHARSET|CHARACTER\s+SET|"
    r"COLLATE)\s*=\s*[\w']+|CHARSET\s*=\s*\w+|COLLATE\s*=\s*\w+|"
    r"AUTO_INCREMENT\s*=\s*\d+|COMMENT\s*=\s*'(?:[^']|'')*'|ROW_FORMAT\s*=\s*\w+|"
    r"TABLESPACE\s+\w+|PARTITION\s+BY[^;]*)",
    re.IGNORECASE,
)
COLUMN = re.compile(r"^(?P<name>" + IDENTIFIER + r")\s*(?P<rest>.*)$", re.DOTALL)


def _unquote(identifier: str) -> str:
    return identifier.strip().strip('"').strip("`").strip("[").strip("]").strip('"').strip()


def _without_comments(text: str, source: str) -> str:
    """Comments removed, quote-aware, with newlines kept so lines still mean something.

    A regex substitution deletes the rest of the line after a `--` inside a string
    literal, so `DEFAULT '--'` corrupted the statement before it was parsed. A
    block comment becomes newlines (never nothing) so removing it cannot join two
    tokens or shift the lines an error is reported against.
    """
    out: list[str] = []
    index = 0
    quote = ""
    while index < len(text):
        character = text[index]
        if quote:
            out.append(character)
            if character == quote:
                if index + 1 < len(text) and text[index + 1] == quote:
                    out.append(text[index + 1])
                    index += 2
                    continue
                quote = ""
            index += 1
            continue
        if character in "'\"":
            quote = character
            out.append(character)
            index += 1
            continue
        if text.startswith("--", index):
            while index < len(text) and text[index] != "\n":
                index += 1
            continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            if end < 0:
                raise InvalidArtifact(f"{source}: an unterminated /* comment")
            inner = text[index:end]
            out.append("".join("\n" if c == "\n" else " " for c in inner))
            index = end + 2
            continue
        out.append(character)
        index += 1
    if quote:
        raise InvalidArtifact(f"{source}: an unterminated {quote} literal")
    return "".join(out)


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


def _mask_literals(text: str) -> str:
    """The text with the contents of single-quoted literals blanked, same length.

    SQL strings are single-quoted; double quotes are identifiers. `REFERENCES` and
    the other clause words are only meaningful outside a literal: measured,
    `DEFAULT 'see REFERENCES users for detail'` invented a foreign key, and
    `DEFAULT 'see references section below'` refused the statement with a diagnosis
    naming a table that does not exist. Blanking keeps every offset, so a line
    number and a slice still mean what they meant.
    """
    out: list[str] = []
    index = 0
    while index < len(text):
        character = text[index]
        if character != "'":
            out.append(character)
            index += 1
            continue
        out.append("'")
        index += 1
        while index < len(text):
            if text[index] == "'":
                if index + 1 < len(text) and text[index + 1] == "'":
                    out.append("  ")  # an escaped quote stays blanked
                    index += 2
                    continue
                out.append("'")
                index += 1
                break
            out.append(" ")
            index += 1
    return "".join(out)


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
    cleaned = _without_comments(text, source)
    tables: dict[str, dict[str, str]] = {}
    primary_keys: dict[str, str] = {}
    foreign_keys: list[tuple[str, str]] = []
    not_modelled: list[tuple[str, str]] = []
    pending: list[tuple[str, str, int]] = []
    position = 0
    found = False
    while True:
        while position < len(cleaned) and cleaned[position] in " \t\r\n":
            position += 1
        if position >= len(cleaned):
            break
        # `match`, never `search`: a statement between two tables must be refused
        # rather than skipped, or an ALTER could add a constraint nothing sees.
        match = CREATE_TABLE.match(cleaned, position)
        if match is None:
            line = _line_of(cleaned, position)
            statement = cleaned[position : position + 40].strip()
            if OTHER_STATEMENT.match(statement):
                raise InvalidArtifact(
                    f"{source}:{line}: only CREATE TABLE is read; "
                    "declare the schema in Python for anything else"
                )
            raise InvalidArtifact(f"{source}:{line}: not a CREATE TABLE statement")
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
        seen_not_modelled: set[str] = set()
        for item_line, item in _items(body, 0, cleaned, open_paren + 1):
            for clause in NOT_MODELLED.findall(_mask_literals(item)):
                seen_not_modelled.add(" ".join(str(clause).upper().split()))
            if INDEX_CLAUSE.match(item):
                seen_not_modelled.add("an index clause")
                continue
            if TABLE_CONSTRAINT.match(item):
                primary, foreign, unresolved = _table_constraint(
                    item, table, f"{source}:{item_line}"
                )
                if primary is not None:
                    primary_keys[table] = primary
                if foreign is not None:
                    foreign_keys.append(foreign)
                if unresolved is not None:
                    pending.append((*unresolved, item_line))
                continue
            column = COLUMN.match(item)
            if column is None:
                raise InvalidArtifact(f"{source}:{item_line}: not a column definition")
            name = _unquote(column.group("name"))
            if name in columns:
                raise InvalidArtifact(f"{source}:{item_line}: column {name!r} is declared twice")
            rest = column.group("rest")
            masked_rest = _mask_literals(rest)
            columns[name] = _column_type(masked_rest)
            reference = REFERENCES.search(masked_rest)
            if reference is not None:
                parent = _unquote(reference.group("table"))
                target = reference.group("column")
                child = f"{table}.{name}"
                if target is None:
                    pending.append((child, parent, item_line))
                else:
                    foreign_keys.append((child, f"{parent}.{_unquote(target)}"))
            if re.search(r"\bPRIMARY\s+KEY\b", masked_rest, re.IGNORECASE):
                if table in primary_keys:
                    raise InvalidArtifact(
                        f"{source}:{item_line}: table {table!r} declares two primary keys"
                    )
                primary_keys[table] = name
        tables[table] = columns
        position = close_paren + 1
        while position < len(cleaned) and cleaned[position] in " \t\r\n":
            position += 1
        # Table options (`) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4`, `) WITHOUT ROWID`)
        # are part of the same statement. Refusing them made every MySQL dump
        # unreadable; they are recognised, recorded as not carried, and skipped.
        while position < len(cleaned) and cleaned[position] != ";":
            option = TABLE_OPTIONS.match(cleaned, position)
            if option is None:
                raise InvalidArtifact(
                    f"{source}:{_line_of(cleaned, position)}: expected ';' after the table "
                    f"body, or a table option this reader knows; found "
                    f"{cleaned[position : position + 24]!r}"
                )
            seen_not_modelled.add("a table option")
            position = option.end()
            while position < len(cleaned) and cleaned[position] in " \t\r\n,":
                position += 1
        position += 1
        if seen_not_modelled:
            not_modelled.append((table, ", ".join(sorted(seen_not_modelled))))
    if not found:
        raise InvalidArtifact(f"{source}: no CREATE TABLE statement")
    for child, parent, line in pending:
        primary = primary_keys.get(parent)
        if primary is None:
            raise InvalidArtifact(
                f"{source}:{line}: {child} references {parent!r} without a column, and "
                f"{parent!r} declares no primary key to mean"
            )
        foreign_keys.append((child, f"{parent}.{primary}"))
    return Schema(
        tables=tables,
        primary_keys=primary_keys,
        foreign_keys=foreign_keys,
        # DDL declares no entry points. Recording it is what tells the checks that
        # the rules *roots* decides — `orphan-table` among them — have nothing to
        # apply: measured, the same schema gained `orphan-table: nothing references
        # 'users'` on this route and was clean on the Python one.
        not_modelled=[
            *not_modelled,
            ("", "the model does not carry `roots`: DDL declares no entry points"),
        ],
        roots_modelled=False,
        name=Path(source).stem or "schema",
    )


def _table_constraint(
    item: str, table: str, where: str
) -> tuple[str | None, tuple[str, str] | None, tuple[str, str] | None]:
    """(primary key column, foreign key pair, unresolved pair) for one constraint.

    The third element is a foreign key whose parent column was omitted, which can
    only be resolved once every table has been read.
    """
    primary = PRIMARY_KEY.match(item)
    if primary is not None:
        columns = _columns_of(primary.group("columns"))
        if len(columns) != 1:
            raise InvalidArtifact(
                f"{where}: a composite primary key on {table!r} is not representable; "
                "declare the schema in Python"
            )
        return columns[0], None, None
    foreign = FOREIGN_KEY.match(item)
    if foreign is not None:
        columns = _columns_of(foreign.group("columns"))
        target = _columns_of(foreign.group("target") or "")
        parent = _unquote(foreign.group("table"))
        # The child count is checked first: returning early to resolve an omitted
        # target used to drop the second column of a composite key silently.
        if len(columns) != 1:
            raise InvalidArtifact(
                f"{where}: a composite foreign key on {table!r} is not representable; "
                "declare the schema in Python"
            )
        if foreign.group("target") is None:
            return None, None, (f"{table}.{columns[0]}", parent)
        if len(target) != 1:
            raise InvalidArtifact(
                f"{where}: a composite foreign key on {table!r} is not representable; "
                "declare the schema in Python"
            )
        return None, (f"{table}.{columns[0]}", f"{parent}.{target[0]}"), None
    return None, None, None


def schema_from_file(path: str | Path) -> Schema:
    """A `Schema` from a SQL DDL file on disk."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InvalidArtifact(f"{path}: {exc}") from exc
    return schema_from_ddl(text, source=str(path))


__all__ = ["schema_from_ddl", "schema_from_file", "type_family"]
