"""The schemagx public helpers and a branch no example exercises."""

from __future__ import annotations

from gxcore import ERROR
from gxcore.diagram import image_size as node_image_size
from gxcore.testing import assert_fires
from schemagx import Schema, inspect_schema, schema_from_parts
from schemagx.render import image_size


def test_schema_from_parts_roundtrips():
    schema = schema_from_parts(tables={"a": {"id": "int"}}, primary_keys={"a": "id"}, roots=["a"])
    assert schema.tables == {"a": {"id": "int"}}
    assert schema.roots == ["a"]


def test_image_size_tracks_the_table_count():
    schema = Schema(tables={"a": {"id": "int"}, "b": {"id": "int"}})
    assert image_size(schema) == node_image_size(2)


def test_a_foreign_key_from_an_undeclared_table():
    schema = Schema(
        tables={"a": {"id": "int"}},
        primary_keys={"a": "id"},
        foreign_keys=[("ghost.id", "a.id")],
        roots=["a"],
    )
    assert_fires(inspect_schema(schema), "dangling-foreign-key", ERROR)


def test_referenced_tables_lists_both_ends():
    schema = Schema(
        tables={"a": {"id": "int"}, "b": {"id": "int"}},
        primary_keys={"a": "id", "b": "id"},
        foreign_keys=[("b.a_id", "a.id")],
        roots=["a"],
    )
    assert schema.referenced_tables() == {"a", "b"}


def test_load_schema_from_module_level_tables(tmp_path):
    from schemagx import load_schema

    src = tmp_path / "tables.py"
    src.write_text(
        'TABLES = {"a": {"id": "int"}}\n'
        'PRIMARY_KEYS = {"a": "id"}\n'
        "FOREIGN_KEYS = []\n"
        'ROOTS = ["a"]\n'
        'NAME = "t"\n'
    )
    schema, _module = load_schema(src)
    assert schema.tables == {"a": {"id": "int"}}
    assert schema.name == "t"
