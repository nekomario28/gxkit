"""The DDL importer: every branch, and the boundaries it refuses to guess."""

from __future__ import annotations

import re

import pytest
from gxcore.loading import InvalidArtifact
from schemagx import (
    Schema,
    inspect_schema,
    load_schema,
    schema_from_ddl,
    schema_from_file,
    type_family,
)

DDL = """
CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    tenant_id INTEGER REFERENCES tenants (id),
    created_at TIMESTAMP WITH TIME ZONE
);
"""


def test_a_schema_file_becomes_tables_and_keys():
    schema = schema_from_ddl(DDL)
    assert schema.name == "schema"
    assert schema.table_names() == ["tenants", "users"]
    assert schema.tables["users"]["email"] == "VARCHAR(255)"
    assert schema.primary_keys == {"tenants": "id", "users": "id"}
    assert schema.foreign_keys == [("users.tenant_id", "tenants.id")]


def test_a_table_level_foreign_key_is_read():
    schema = schema_from_ddl(
        "CREATE TABLE a (id INT PRIMARY KEY);\n"
        "CREATE TABLE b (a_id INT, CONSTRAINT b_a_fkey FOREIGN KEY (a_id) REFERENCES a (id));\n"
    )
    assert schema.foreign_keys == [("b.a_id", "a.id")]


def test_a_foreign_key_without_a_column_means_the_primary_key():
    """SQL means the referenced table's primary key, whatever it is called."""
    schema = schema_from_ddl(
        "CREATE TABLE a (key INT PRIMARY KEY);\nCREATE TABLE b (a_key INT REFERENCES a);\n"
    )
    assert schema.foreign_keys == [("b.a_key", "a.key")]


def test_a_table_level_foreign_key_without_a_column_means_the_primary_key():
    schema = schema_from_ddl(
        "CREATE TABLE a (key INT PRIMARY KEY);\n"
        "CREATE TABLE b (a_key INT, FOREIGN KEY (a_key) REFERENCES a);\n"
    )
    assert schema.foreign_keys == [("b.a_key", "a.key")]


def test_a_reference_to_a_table_without_a_primary_key_is_refused():
    with pytest.raises(InvalidArtifact, match="no primary key"):
        schema_from_ddl(
            "CREATE TABLE a (x INT);\nCREATE TABLE b (y INT REFERENCES a);\n",
            source="schema.sql",
        )


def test_a_reference_may_name_a_table_declared_later():
    schema = schema_from_ddl(
        "CREATE TABLE b (a_key INT REFERENCES a);\nCREATE TABLE a (key INT PRIMARY KEY);\n"
    )
    assert schema.foreign_keys == [("b.a_key", "a.key")]


def test_a_literal_may_contain_an_escaped_quote_and_a_comment_marker():
    schema = schema_from_ddl(
        "CREATE TABLE t (id INT PRIMARY KEY, note TEXT DEFAULT 'it''s -- fine');\n"
    )
    assert schema.tables["t"]["note"] == "TEXT"


def test_a_block_comment_between_tokens_becomes_separators():
    """Removing it must not join tokens or shift the lines an error names."""
    schema = schema_from_ddl("CREATE TABLE t (id INT /* a\n   b */ PRIMARY KEY);\n")
    assert schema.primary_keys == {"t": "id"}


@pytest.mark.parametrize(
    ("ddl", "expected"),
    [
        ("CREATE TABLE t (id INT); /* never closed\n", "unterminated /* comment"),
        ("CREATE TABLE t (id INT, x TEXT DEFAULT 'oops);\n", "unterminated ' literal"),
        ('CREATE TABLE t (id INT, x TEXT DEFAULT "oops);\n', 'unterminated " literal'),
    ],
)
def test_an_unterminated_comment_or_literal_is_refused(ddl, expected):
    with pytest.raises(InvalidArtifact, match=re.escape(expected)):
        schema_from_ddl(ddl, source="schema.sql")


def test_a_composite_target_is_refused():
    with pytest.raises(InvalidArtifact, match="composite foreign key"):
        schema_from_ddl(
            "CREATE TABLE p (x INT, y INT, PRIMARY KEY (x));\n"
            "CREATE TABLE c (a INT, FOREIGN KEY (a) REFERENCES p (x, y));\n",
            source="schema.sql",
        )


def test_a_statement_between_two_tables_is_refused_not_skipped():
    """Searching past an ALTER would drop the constraint it adds."""
    with pytest.raises(InvalidArtifact, match="only CREATE TABLE"):
        schema_from_ddl(
            "CREATE TABLE a (id INT);\nALTER TABLE a ADD COLUMN x INT;\nCREATE TABLE b (id INT);\n",
            source="schema.sql",
        )


def test_a_table_level_primary_key_is_read():
    schema = schema_from_ddl("CREATE TABLE a (id INT, PRIMARY KEY (id));\n")
    assert schema.primary_keys == {"a": "id"}


def test_an_inline_primary_key_is_read():
    schema = schema_from_ddl("CREATE TABLE a (id INT PRIMARY KEY, name TEXT);\n")
    assert schema.primary_keys == {"a": "id"}


def test_quoted_and_bracketed_identifiers_are_unquoted():
    schema = schema_from_ddl(
        'CREATE TABLE "order items" (`id` INT PRIMARY KEY);\n'
        "CREATE TABLE [logs] ([entry_id] INT REFERENCES [order items] (id));\n"
    )
    assert schema.table_names() == ["order items", "logs"]
    assert schema.foreign_keys == [("logs.entry_id", "order items.id")]


def test_comments_and_blank_lines_are_not_statements():
    schema = schema_from_ddl("-- a comment\n/* a block\ncomment */\nCREATE TABLE a (id INT);\n")
    assert schema.table_names() == ["a"]


def test_create_table_if_not_exists_is_read():
    schema = schema_from_ddl("CREATE TABLE IF NOT EXISTS a (id INT);\n")
    assert schema.table_names() == ["a"]


@pytest.mark.parametrize(
    ("declared", "type_of"),
    [
        ("VARCHAR(255)", "VARCHAR(255)"),
        ("CHARACTER VARYING(255)", "CHARACTER VARYING(255)"),
        ("NUMERIC(10, 2)", "NUMERIC(10, 2)"),
        ("DECIMAL(10,2)", "DECIMAL(10,2)"),
        ("TIMESTAMP WITH TIME ZONE", "TIMESTAMP WITH TIME ZONE"),
        ("DOUBLE PRECISION", "DOUBLE PRECISION"),
        ("INT UNSIGNED", "INT"),
        ("INT NOT NULL DEFAULT 0", "INT"),
        ('TEXT COLLATE "C"', "TEXT"),
        ("SERIAL", "SERIAL"),
        ("TIMESTAMP WITH TIME ZONE NOT NULL", "TIMESTAMP WITH TIME ZONE"),
    ],
)
def test_a_declared_type_is_read_without_its_constraints(declared, type_of):
    schema = schema_from_ddl(f"CREATE TABLE a (id {declared});\n")
    assert schema.tables["a"]["id"] == type_of


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("INT", "INTEGER"),
        ("INTEGER", "INT4"),
        ("SERIAL", "INTEGER"),
        ("BIGSERIAL", "BIGINT"),
        ("SMALLINT", "INT2"),
        ("BOOL", "BOOLEAN"),
        ("VARCHAR(50)", "CHARACTER VARYING(255)"),
        ("TIMESTAMPTZ", "TIMESTAMP WITH TIME ZONE"),
        ("DOUBLE PRECISION", "FLOAT8"),
        ("DECIMAL(10,2)", "NUMERIC"),
    ],
)
def test_synonymous_types_are_the_same_family(left, right):
    assert type_family(left) == type_family(right)


@pytest.mark.parametrize(
    ("left", "right"), [("INT", "TEXT"), ("SERIAL", "VARCHAR(255)"), ("UUID", "INT")]
)
def test_different_types_are_different_families(left, right):
    assert type_family(left) != type_family(right)


def test_the_same_schema_spelled_two_ways_is_not_a_type_mismatch():
    schema = schema_from_ddl(
        "CREATE TABLE a (id SERIAL PRIMARY KEY);\n"
        "CREATE TABLE b (a_id INTEGER REFERENCES a (id));\n"
    )
    report = inspect_schema(schema)
    assert "fk-type-mismatch" not in {problem.code for problem in report.problems}


def test_a_real_mismatch_is_still_reported():
    schema = schema_from_ddl(
        "CREATE TABLE a (email VARCHAR(255) PRIMARY KEY);\n"
        "CREATE TABLE b (a_email INTEGER REFERENCES a (email));\n"
    )
    report = inspect_schema(schema)
    assert "fk-type-mismatch" in {problem.code for problem in report.problems}


def test_the_defects_a_dump_really_has_are_reported():
    schema = schema_from_ddl(
        "CREATE TABLE users (id SERIAL PRIMARY KEY, email VARCHAR(255));\n"
        "CREATE TABLE posts (author_id INTEGER, "
        "FOREIGN KEY (author_id) REFERENCES users (email));\n"
    )
    report = inspect_schema(schema)
    codes = {problem.code for problem in report.problems}
    # `posts` really has no primary key of its own, so that finding is true too.
    assert codes == {"fk-type-mismatch", "fk-to-non-primary-key", "missing-primary-key"}


def test_a_file_is_read_as_ddl(tmp_path):
    document = tmp_path / "schema.sql"
    document.write_text(DDL, encoding="utf-8")
    schema = schema_from_file(document)
    assert schema.table_names() == ["tenants", "users"]
    assert schema.name == "schema"
    loaded, _module = load_schema(document)
    assert loaded.tables == schema.tables


def test_a_missing_file_is_an_input_failure(tmp_path):
    with pytest.raises(InvalidArtifact, match=r"schema\.sql"):
        schema_from_file(tmp_path / "schema.sql")


@pytest.mark.parametrize(
    ("ddl", "expected"),
    [
        ("", "no CREATE TABLE statement"),
        ("SELECT 1;\n", "not a CREATE TABLE statement"),
        ("CREATE TABLE a (id INT\n", "never closed"),
        ("CREATE TABLE a (id INT);\nCREATE TABLE a (x INT);\n", "is created twice"),
        ("CREATE TABLE a (id INT);\nALTER TABLE a ADD COLUMN x INT;\n", "only CREATE TABLE"),
        ("CREATE TABLE a (id INT, id TEXT);\n", "column 'id' is declared twice"),
        ("CREATE TABLE a (id);\n", "declares no type"),
        ("CREATE TABLE a (id INT, PRIMARY KEY (id, x));\n", "composite primary key"),
        (
            "CREATE TABLE a (id INT);\nCREATE TABLE b (a_id INT, x INT, "
            "FOREIGN KEY (a_id, x) REFERENCES a (id));\n",
            "composite foreign key",
        ),
        (
            "CREATE TABLE a (id INT PRIMARY KEY, x INT PRIMARY KEY);\n",
            "declares two primary keys",
        ),
    ],
)
def test_a_file_that_is_not_readable_ddl_says_where_it_is_wrong(ddl, expected):
    with pytest.raises(InvalidArtifact) as info:
        schema_from_ddl(ddl, source="schema.sql")
    assert expected in str(info.value)


def test_a_statement_that_does_not_end_where_it_should_says_so():
    with pytest.raises(InvalidArtifact, match="expected ';' after the table body"):
        schema_from_ddl("CREATE TABLE a (id INT) extra\n", source="schema.sql")


def test_an_item_that_is_neither_a_constraint_nor_a_column_is_reported():
    with pytest.raises(InvalidArtifact, match="not a column definition"):
        schema_from_ddl("CREATE TABLE a ((id) INT);\n", source="schema.sql")


def test_a_table_constraint_that_is_neither_key_is_skipped(tmp_path):
    schema = schema_from_ddl(
        "CREATE TABLE a (id INT, CHECK (id > 0), UNIQUE (id));\n", source="schema.sql"
    )
    assert schema.foreign_keys == [] and schema.primary_keys == {}


def test_a_python_declaration_is_still_the_other_route(tmp_path):
    artifact = tmp_path / "schema.py"
    artifact.write_text(
        "from schemagx import Schema\n"
        'schema = Schema(tables={"a": {"id": "int"}}, primary_keys={"a": "id"})\n',
        encoding="utf-8",
    )
    from schemagx import load_schema

    schema, _module = load_schema(artifact)
    assert isinstance(schema, Schema)
    assert schema.table_names() == ["a"]
