"""Prove every schemagx check fires on a schema that has the fault."""

from __future__ import annotations

from pathlib import Path

from gxcore import ERROR, INFO, WARN
from gxcore.testing import assert_fires, assert_quiet
from schemagx import Schema, inspect_schema, load_schema

GOOD = Schema(
    tables={
        "users": {"id": "int", "email": "text"},
        "posts": {"id": "int", "author_id": "int"},
        "comments": {"id": "int", "post_id": "int"},
    },
    primary_keys={"users": "id", "posts": "id", "comments": "id"},
    foreign_keys=[("posts.author_id", "users.id"), ("comments.post_id", "posts.id")],
    roots=["users"],
    name="good",
)


def test_good_schema_has_no_problems():
    assert inspect_schema(GOOD).problems == []


def test_dangling_parent_table():
    s = Schema(
        tables={"a": {"id": "int"}},
        primary_keys={"a": "id"},
        foreign_keys=[("a.x", "ghost.id")],
        roots=["a"],
        name="x",
    )
    assert_fires(inspect_schema(s), "dangling-foreign-key", ERROR)


def test_dangling_column():
    s = Schema(
        tables={"a": {"id": "int"}, "b": {"id": "int"}},
        primary_keys={"a": "id", "b": "id"},
        foreign_keys=[("a.b_id", "b.missing")],
        roots=["a"],
        name="x",
    )
    assert_fires(inspect_schema(s), "dangling-foreign-key", ERROR)


def test_type_mismatch():
    s = Schema(
        tables={"a": {"id": "int"}, "b": {"id": "text"}},
        primary_keys={"a": "id", "b": "id"},
        foreign_keys=[("b.id", "a.id")],
        roots=["a"],
        name="x",
    )
    assert_fires(inspect_schema(s), "fk-type-mismatch", WARN)


def test_cycle():
    s = Schema(
        tables={"a": {"id": "int", "b_id": "int"}, "b": {"id": "int", "a_id": "int"}},
        primary_keys={"a": "id", "b": "id"},
        foreign_keys=[("a.b_id", "b.id"), ("b.a_id", "a.id")],
        roots=["a"],
        name="x",
    )
    assert_fires(inspect_schema(s), "cyclic-foreign-key", WARN)


def test_self_reference_is_not_a_cycle():
    s = Schema(
        tables={"users": {"id": "int", "manager_id": "int"}},
        primary_keys={"users": "id"},
        foreign_keys=[("users.manager_id", "users.id")],
        roots=["users"],
        name="x",
    )
    assert_quiet(inspect_schema(s), "cyclic-foreign-key")


def test_missing_primary_key():
    s = Schema(tables={"a": {"id": "int"}}, roots=["a"], name="x")
    assert_fires(inspect_schema(s), "missing-primary-key", INFO)


def test_orphan_table():
    s = Schema(
        tables={"a": {"id": "int"}, "lonely": {"id": "int"}},
        primary_keys={"a": "id", "lonely": "id"},
        roots=["a"],
        name="x",
    )
    r = inspect_schema(s)
    assert_fires(r, "orphan-table", INFO)
    # a leaf that references a parent is not an orphan
    assert_quiet(inspect_schema(GOOD), "orphan-table")


def test_fk_to_non_primary_key():
    s = Schema(
        tables={"a": {"id": "int", "code": "int"}, "b": {"id": "int"}},
        primary_keys={"a": "id", "b": "id"},
        foreign_keys=[("b.id", "a.code")],
        roots=["a"],
        name="x",
    )
    assert_fires(inspect_schema(s), "fk-to-non-primary-key", WARN)


def test_examples_load_and_are_diagnosed():
    examples = Path(__file__).resolve().parents[1] / "examples"
    good, _ = load_schema(examples / "good_schema.py")
    broken, _ = load_schema(examples / "broken_schema.py")
    assert inspect_schema(good).errors == 0
    r = inspect_schema(broken)
    assert_fires(r, "dangling-foreign-key", ERROR)
    assert_fires(r, "cyclic-foreign-key", WARN)
    assert_fires(r, "missing-primary-key", INFO)
    assert_fires(r, "orphan-table", INFO)


def test_a_root_that_is_not_a_table_is_reported():
    schema = Schema(tables={"t": {"id": "int"}}, primary_keys={"t": "id"}, roots=["ghost"])
    report = inspect_schema(schema)
    assert_fires(report, "dangling-reference", ERROR)
    assert "not a declared table" in report.problems[0].message


def test_a_reference_to_a_table_with_no_primary_key_cannot_be_to_one():
    """`fk-to-non-primary-key` = the reference is not to a primary key.

    Adversarial case from an independent semantics audit: the artifact exited 0 with
    only `missing-primary-key` on the *other* table.
    """
    schema = Schema(
        tables={"posts": {"id": "int", "tag_name": "text"}, "tags": {"name": "text"}},
        primary_keys={"posts": "id"},
        foreign_keys=[("posts.tag_name", "tags.name")],
        roots=["posts"],
    )
    report = inspect_schema(schema)
    fired = [problem for problem in report.problems if problem.code == "fk-to-non-primary-key"]
    assert len(fired) == 1
    assert "declares no primary key" in fired[0].message
