"""Prove every depsgx check fires on a graph that has the fault."""

from __future__ import annotations

from pathlib import Path

from depsgx import ModuleGraph, inspect_graph, load_graph
from gxcore import ERROR, INFO
from gxcore.testing import assert_fires, assert_quiet

GOOD = ModuleGraph(
    modules=["api", "service", "domain", "util"],
    depends=[("api", "service"), ("service", "domain"), ("domain", "util")],
    roots=["api"],
    layers=[["api"], ["service"], ["domain"], ["util"]],
    name="good",
)


def test_good_graph_has_no_problems():
    assert inspect_graph(GOOD).problems == []


def test_cycle():
    g = ModuleGraph(modules=["a", "b"], depends=[("a", "b"), ("b", "a")], roots=["a"], name="x")
    assert_fires(inspect_graph(g), "cycle", ERROR)


def test_reports_each_independent_cyclic_component_and_keeps_fixed_ones_quiet():
    first = [("a", "b"), ("b", "a")]
    second = [("c", "d"), ("d", "c")]
    for edges, expected in [
        (first + second, 2),
        ([*first, ("c", "d")], 1),
        ([("a", "b"), *second], 1),
        ([("a", "b"), ("c", "d")], 0),
    ]:
        graph = ModuleGraph(modules=["a", "b", "c", "d"], depends=edges, roots=["a", "c"])
        cycles = [p for p in inspect_graph(graph).problems if p.code == "cycle"]
        assert len(cycles) == expected
        if expected == 2:
            assert sum(p.target in {"a", "b"} for p in cycles) == 1
            assert sum(p.target in {"c", "d"} for p in cycles) == 1


def test_reports_one_representative_not_every_circuit_within_a_component():
    graph = ModuleGraph(
        modules=["a", "b", "c"],
        depends=[("a", "b"), ("b", "a"), ("a", "c"), ("c", "a")],
        roots=["a"],
    )
    assert len([p for p in inspect_graph(graph).problems if p.code == "cycle"]) == 1


def test_dangling_dependency():
    g = ModuleGraph(modules=["a"], depends=[("a", "ghost")], roots=["a"], name="x")
    assert_fires(inspect_graph(g), "dangling-dependency", ERROR)


def test_self_dependency():
    g = ModuleGraph(modules=["a", "b"], depends=[("a", "a"), ("a", "b")], roots=["a"], name="x")
    assert_fires(inspect_graph(g), "self-dependency", ERROR)
    # ...and it is not also reported as a cycle (no double-counting).
    assert_quiet(inspect_graph(g), "cycle")


def test_forbidden_dependency():
    g = ModuleGraph(
        modules=["domain", "infra"],
        depends=[("domain", "infra")],
        roots=["domain"],
        forbidden=[("domain", "infra")],
        name="x",
    )
    assert_fires(inspect_graph(g), "forbidden-dependency", ERROR)


def test_layer_violation():
    g = ModuleGraph(
        modules=["api", "util"],
        depends=[("api", "util"), ("util", "api")],
        roots=["api"],
        layers=[["api"], ["util"]],
        name="x",
    )
    assert_fires(inspect_graph(g), "layer-violation", ERROR)


def test_downward_dependency_is_fine():
    assert_quiet(inspect_graph(GOOD), "layer-violation")


def test_unreachable_module_is_info():
    g = ModuleGraph(modules=["api", "dead"], depends=[("api", "api")], roots=["api"], name="x")
    assert_fires(inspect_graph(g), "unreachable-module", INFO)


def test_orphan_module_is_info():
    g = ModuleGraph(modules=["api", "leaf"], depends=[("api", "api")], roots=["api"], name="x")
    assert_fires(inspect_graph(g), "orphan-module", INFO)


def test_no_roots_is_info():
    g = ModuleGraph(modules=["a", "b"], depends=[("a", "b")], name="x")
    assert_fires(inspect_graph(g), "no-roots", INFO)


def test_duplicate_dependency_is_info():
    g = ModuleGraph(modules=["a", "b"], depends=[("a", "b"), ("a", "b")], roots=["a"], name="x")
    assert_fires(inspect_graph(g), "duplicate-dependency", INFO)


def test_examples_load_and_are_diagnosed():
    examples = Path(__file__).resolve().parents[1] / "examples"
    good, _ = load_graph(examples / "good_modules.py")
    broken, _ = load_graph(examples / "broken_modules.py")
    assert inspect_graph(good).errors == 0
    r = inspect_graph(broken)
    for code in (
        "cycle",
        "layer-violation",
        "forbidden-dependency",
        "self-dependency",
        "dangling-dependency",
    ):
        assert_fires(r, code, ERROR)
    assert_fires(r, "unreachable-module", INFO)


def test_a_declared_rule_that_names_nothing_is_reported():
    """A typo'd rule must not silently stop being a rule."""
    graph = ModuleGraph(modules=["a", "b"], depends=[("a", "b")], roots=["a"])
    assert inspect_graph(graph).errors == 0

    table = [
        ("forbidden", {"forbidden": [("ghost", "b")]}),
        ("layers", {"layers": {"L": ["ghost"]}}),
        ("roots", {"roots": ["ghost"]}),
    ]
    for field, extra in table:
        report = inspect_graph(
            ModuleGraph(**(dict(modules=["a", "b"], depends=[("a", "b")], roots=["a"]) | extra))
        )
        assert_fires(report, "dangling-reference", ERROR), field
        assert field in report.problems[0].message


def test_a_self_edge_is_not_a_user_of_the_module():
    """`orphan-module` = "nothing depends on it", and a module is not something else.

    Adversarial case from an independent semantics audit: a module whose only in-edge
    was its own self-loop was reported as depended-upon.
    """
    graph = ModuleGraph(modules=["a", "b", "c"], depends=[("a", "b"), ("c", "c")], roots=["a"])
    report = inspect_graph(graph)
    assert_fires(report, "orphan-module", INFO)
    assert {problem.target for problem in report.problems if problem.code == "orphan-module"} == {
        "c"
    }
