"""Boundary cases use public declarations, not private converter details."""

from __future__ import annotations

import pytest
from apigx import API, Endpoint, inspect_api
from crongx import Run, Schedule, inspect_schedule, load_schedule
from envgx import Environment, inspect_environment
from gxkit.cli import main
from netgx import Network, inspect_network


def test_abbreviated_run_tuples_keep_the_unshared_resource_default(tmp_path):
    path = tmp_path / "artifact.py"
    path.write_text('RUNS = [("a", 0, 10), ("b", 5, 10)]\n', encoding="utf-8")
    schedule, _ = load_schedule(path)
    assert [run.resource for run in schedule.runs] == ["", ""]
    assert not inspect_schedule(schedule).errors


@pytest.mark.parametrize("empty", [Run("empty", 5, 0, "r"), Run("invalid", 5, -1, "r")])
def test_empty_or_reversed_intervals_never_overlap(empty):
    schedule = Schedule([Run("active", 0, 10, "r"), empty])
    assert not schedule.overlap(*schedule.runs)
    assert not schedule.overlap(*reversed(schedule.runs))
    assert "overlap" not in {p.code for p in inspect_schedule(schedule).problems}


@pytest.mark.parametrize(
    ("start", "duration"),
    [
        (float("nan"), 1),
        (0, float("nan")),
        (float("inf"), 1),
        (0, float("inf")),
        (-float("inf"), 1),
        (1e308, 1e308),
    ],
)
def test_nonfinite_time_cannot_be_certified_or_used_for_overlap(start, duration):
    schedule = Schedule([Run("invalid", start, duration, "r"), Run("normal", 0, 10, "r")])
    report = inspect_schedule(schedule)
    assert report.errors and "non-finite-time" in {p.code for p in report.problems}
    assert not schedule.overlap(*schedule.runs)


@pytest.mark.parametrize("seed", ["-0.5", "0.5", "True", '"42"', 'float("nan")', 'float("inf")'])
@pytest.mark.parametrize("shape", ["tuple", "mapping", "dataclass"])
def test_seed_declarations_reject_noninteger_values_without_truncation(tmp_path, seed, shape):
    member = f'("bad", {seed})' if shape == "tuple" else f'{{"name":"bad","seed":{seed}}}'
    source = f"STREAMS = [{member}]\n"
    if shape == "dataclass":
        source = f'from seedgx import SeedSpec, Stream\nspec = SeedSpec([Stream("bad", {seed})])\n'
    path = tmp_path / "artifact.py"
    path.write_text(source, encoding="utf-8")
    assert main(["inspect", "seedgx", str(path), "--no-storyboard", "--no-config"]) == 2


@pytest.mark.parametrize(
    ("tool", "source", "expected"),
    [
        ("crongx", 'RUNS = [("bad",0,1,"r","extra")]\n', 2),
        ("crongx", 'schedule = {"runs": 42}\n', 2),
        ("seedgx", 'STREAMS = [("bad",1,"extra")]\n', 2),
        ("pipegx", 'STEPS = [("bad",[],"extra")]\n', 2),
        ("apigx", 'ENDPOINTS = [("GET","/v1/a","extra")]\n', 2),
        ("seedgx", 'STREAMS = [("missing", None)]\n', 1),
    ],
)
def test_invalid_container_or_extra_fields_are_rejected_and_none_is_missing(
    tmp_path, tool, source, expected
):
    path = tmp_path / "artifact.py"
    path.write_text(source, encoding="utf-8")
    assert main(["inspect", tool, str(path), "--no-storyboard", "--no-config"]) == expected


def test_empty_environment_still_checks_references():
    report = inspect_environment(Environment(variables=[], references=["DATABASE_URL"]))
    assert [p.label for p in report.problems if p.code == "undeclared-reference"] == [
        "DATABASE_URL"
    ]


def test_empty_network_still_checks_edge_endpoints():
    report = inspect_network(Network(nodes={}, edges=[("missing_a", "missing_b")]))
    assert len([p for p in report.problems if p.code == "dangling-edge"]) == 2


@pytest.mark.parametrize(
    ("tool", "report_factory", "code"),
    [
        (
            "depsgx",
            lambda: __import__("depsgx").inspect_graph(
                __import__("depsgx").ModuleGraph(
                    modules=["a", "b", "c", "d"],
                    depends=[("a", "b"), ("b", "a"), ("c", "d"), ("d", "c")],
                )
            ),
            "cycle",
        ),
        (
            "authzgx",
            lambda: __import__("authzgx").inspect_auth(
                __import__("authzgx").AuthModel(
                    roles=["r1", "r2", "r3", "r4"],
                    inherits=[("r1", "r2"), ("r2", "r1"), ("r3", "r4"), ("r4", "r3")],
                )
            ),
            "cyclic-inheritance",
        ),
        (
            "pipegx",
            lambda: __import__("pipegx").inspect_pipeline(
                __import__("pipegx").Pipeline(
                    steps=[
                        __import__("pipegx").Step("a", needs=["b"]),
                        __import__("pipegx").Step("b", needs=["a"]),
                        __import__("pipegx").Step("c", needs=["d"]),
                        __import__("pipegx").Step("d", needs=["c"]),
                    ]
                )
            ),
            "cycle",
        ),
        (
            "flowgx",
            lambda: __import__("flowgx").inspect_machine(
                __import__("flowgx").Machine(
                    states=["a", "b", "c", "d"],
                    transitions=[("a", "b"), ("b", "a"), ("c", "d"), ("d", "c")],
                    start="a",
                    accept=["a"],
                )
            ),
            "cycle",
        ),
        (
            "protogx",
            lambda: __import__("protogx").inspect_protocol(
                __import__("protogx").Protocol(
                    states=["a", "b", "c", "d"],
                    transitions=[
                        ("a", "b", "m"),
                        ("b", "a", "m"),
                        ("c", "d", "m"),
                        ("d", "c", "m"),
                    ],
                )
            ),
            "cycle",
        ),
        (
            "schemagx",
            lambda: __import__("schemagx").inspect_schema(
                __import__("schemagx").Schema(
                    tables={
                        "a": {"id": "int"},
                        "b": {"id": "int", "a_id": "int"},
                        "c": {"id": "int"},
                        "d": {"id": "int", "c_id": "int"},
                    },
                    primary_keys={"a": "id", "b": "id", "c": "id", "d": "id"},
                    foreign_keys=[
                        ("b.a_id", "a.id"),
                        ("a.id", "b.id"),
                        ("d.c_id", "c.id"),
                        ("c.id", "d.id"),
                    ],
                )
            ),
            "cyclic-foreign-key",
        ),
    ],
)
def test_every_independent_cycle_is_a_finding_not_only_the_first(tool, report_factory, code):
    """A single global cycle search hides the second component.

    Measured before this was fixed: depsgx, authzgx, pipegx and schemagx each
    reported one cycle for a graph with two, so a gate passed with the other one
    present. Each finding is identified by its component, so a witness that
    rotates is the same finding.
    """
    found = [p for p in report_factory().problems if p.code == code]
    assert len(found) == 2, f"{tool}: {[(p.target, p.identity) for p in found]}"
    components = [p.identity for p in found]
    assert len(set(components)) == 2 and all(components), components


@pytest.mark.parametrize(
    ("base", "path", "warn"),
    [
        ("/v1", "/v10/users", True),
        ("/v1", "/v1", False),
        ("/v1", "/v1/users", False),
        ("/v1/", "/v1/users", False),
        ("/v1/", "/v10/users", True),
        ("/", "/users", False),
        ("/", "relative", True),
        ("", "relative", False),
    ],
)
def test_api_version_prefix_matches_a_path_boundary(base, path, warn):
    report = inspect_api(API([Endpoint("GET", path, statuses=[200, 404])], base=base))
    assert ("unversioned-path" in {p.code for p in report.problems}) is warn
