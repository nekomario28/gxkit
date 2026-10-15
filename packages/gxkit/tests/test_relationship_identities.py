"""A replaced relationship is new debt, for every finding that can repeat.

The eight fixes in this file are one property: the finding is *about* a
relationship, so its baseline fingerprint names that relationship. Two of the same
kind in one artifact are two findings, and swapping one for another is new debt —
measured per tool, not assumed from the shape of the code.
"""

from __future__ import annotations

from authzgx import AuthModel, inspect_auth
from envgx import Environment, inspect_environment
from gxcore import ERROR
from gxcore.baseline import Baseline, compare
from gxcore.testing import assert_fires
from pipegx import Pipeline, Step, inspect_pipeline
from protogx import Protocol, inspect_protocol
from schemagx import Schema, inspect_schema


def replaced(inspect, before, after) -> dict[str, int]:
    """The baseline summary when `after` replaces `before`, both inspected."""
    return compare(inspect(after), Baseline.of(inspect(before))).as_dict()


def test_a_pipeline_with_two_unproduced_goals_reports_two():
    def pipeline(goals: list[str]):
        return Pipeline(steps=[Step("build", produces=["app"])], goals=goals)

    report = inspect_pipeline(pipeline(["x", "y"]))
    found = [p for p in report.problems if p.code == "goal-not-produced"]
    assert len(found) == 2, [p.identity for p in found]
    assert {p.identity for p in found} == {("x",), ("y",)}

    # Swapping which goal is missing is a new error, not unchanged debt. One
    # finding each: the pipeline is otherwise identical.
    diff = replaced(inspect_pipeline, pipeline(["x"]), pipeline(["y"]))
    assert diff == {"new": 1, "fixed": 1, "persisted": 0, "new_errors": 1}, diff


def test_a_protocol_with_two_unhandled_messages_reports_two():
    """The messages the transitions do not use, one finding each."""

    def protocol(unused: list[str]):
        return Protocol(
            states=["a", "b"],
            messages=["used", *unused],
            transitions=[("a", "b", "used"), ("b", "a", "used")],
        )

    report = inspect_protocol(protocol(["u1", "u2"]))
    found = [p for p in report.problems if p.code == "unhandled-message"]
    assert {p.identity for p in found} == {("u1",), ("u2",)}

    diff = replaced(inspect_protocol, protocol(["u1"]), protocol(["u2"]))
    assert diff["new_errors"] == 1, diff


def test_two_unknown_states_in_a_protocol_are_two_findings():
    def protocol(to: str):
        return Protocol(
            states=["a", "b"],
            messages=["m"],
            transitions=[("a", to, "m")],
        )

    report = inspect_protocol(protocol("ghost"))
    assert_fires(report, "unknown-state", ERROR)
    assert {p.identity for p in report.problems if p.code == "unknown-state"} == {
        (f"transition:a->{to}", to) for to in ("ghost",)
    }
    diff = replaced(inspect_protocol, protocol("ghost"), protocol("phantom"))
    assert diff["new_errors"] == 1, diff


def test_two_dangling_grants_are_two_findings():
    def model(role: str):
        return AuthModel(roles=["admin"], permissions=["read"], grants=[(role, "read")])

    report = inspect_auth(model("ghost"))
    assert_fires(report, "dangling-grant", ERROR)
    diff = replaced(inspect_auth, model("ghost"), model("phantom"))
    assert diff["new_errors"] == 1, diff


def test_a_dangling_assignment_and_inheritance_are_identified_by_the_relationship():
    def assigned(principal: str):
        return AuthModel(
            principals=["u"],
            roles=["admin"],
            permissions=["read"],
            assigned=[(principal, "admin")],
            grants=[("admin", "read")],
        )

    diff = replaced(inspect_auth, assigned("ghost"), assigned("phantom"))
    assert diff["new_errors"] == 1, diff

    def inherits(parent: str):
        # The parent is deliberately *not* declared: that is the dangling role.
        return AuthModel(
            roles=["admin"],
            permissions=["read"],
            inherits=[("admin", parent)],
            grants=[("admin", "read")],
        )

    diff = replaced(inspect_auth, inherits("ghost"), inherits("phantom"))
    assert diff["new_errors"] == 1, diff


def test_two_dangling_foreign_keys_are_two_findings():
    def schema(parent_column: str):
        return Schema(
            tables={"a": {"id": "int"}, "b": {"a_id": "int"}},
            primary_keys={"a": "id", "b": "id"},
            foreign_keys=[("b.a_id", f"a.{parent_column}")],
        )

    report = inspect_schema(schema("missing"))
    assert_fires(report, "dangling-foreign-key", ERROR)
    diff = replaced(inspect_schema, schema("missing"), schema("absent"))
    assert diff["new_errors"] == 1, diff


def test_an_environment_keeps_its_references_distinguishable_by_label():
    """`undeclared-reference` carries a label, so it was never debt."""

    def env(references: list[str]):
        return Environment(variables=[], references=references)

    report = inspect_environment(env(["A", "B"]))
    found = [p for p in report.problems if p.code == "undeclared-reference"]
    assert {p.label for p in found} == {"A", "B"}
    diff = replaced(inspect_environment, env(["A"]), env(["B"]))
    assert diff["new_errors"] == 1, diff
