"""Cross-check schemagx's graph reading against NetworkX.

The schema checks decide "is there a cycle", "is this table an orphan". Those are
graph questions, and the risk is that the *interpretation* — which edges count,
which nodes are isolated — drifts from the definition. So every random schema is
also read by NetworkX and the two verdicts must agree.
"""

from __future__ import annotations

import random

import networkx as nx
import pytest
from gxcore import ERROR
from gxcore.testing import assert_fires
from schemagx import Schema, inspect_schema

SEEDS = range(30)


def _sound_schema(rng: random.Random) -> Schema:
    """A forest of tables, every FK pointing at the parent's primary key."""
    n = rng.randint(1, 10)
    tables: dict[str, dict[str, str]] = {f"t{i}": {"id": "int"} for i in range(n)}
    fks: list[tuple[str, str]] = []
    for i in range(1, n):
        parent = rng.randrange(i)
        tables[f"t{i}"][f"p{i}"] = "int"
        fks.append((f"t{i}.p{i}", f"t{parent}.id"))
    return Schema(
        tables=tables,
        primary_keys={t: "id" for t in tables},
        foreign_keys=fks,
        roots=["t0"],
        name="sound",
    )


def _any_schema(rng: random.Random) -> Schema:
    n = rng.randint(1, 10)
    tables: dict[str, dict[str, str]] = {f"t{i}": {"id": "int", "x": "int"} for i in range(n)}
    names = list(tables)
    fks: list[tuple[str, str]] = []
    for _ in range(rng.randint(0, n * 2)):
        child = rng.choice(names)
        parent = rng.choice(names)
        col = "id" if parent == child else "x"
        fks.append((f"{child}.{col}", f"{parent}.id"))
    return Schema(
        tables=tables,
        primary_keys={t: "id" for t in tables},
        foreign_keys=fks,
        roots=rng.sample(names, rng.randint(0, min(2, n))),
        name="any",
    )


def _nx_graph(schema: Schema) -> nx.DiGraph:
    g: nx.DiGraph = nx.DiGraph()
    g.add_nodes_from(schema.edges())
    for child, parent in schema.foreign_keys:
        g.add_edge(schema.split(child)[0], schema.split(parent)[0])
    return g


def _nx_has_cycle(schema: Schema) -> bool:
    g: nx.DiGraph = nx.DiGraph()
    g.add_nodes_from(schema.table_names())
    for child, parent in schema.foreign_keys:
        ct, _ = schema.split(child)
        pt, _ = schema.split(parent)
        if ct != pt:  # a self-reference is a tree, not a cycle
            g.add_edge(ct, pt)
    return not nx.is_directed_acyclic_graph(g)


def _nx_orphans(schema: Schema) -> set[str]:
    g = _nx_graph(schema)
    return {t for t in schema.table_names() if t not in schema.roots and g.degree(t) == 0}


def _targets(report, code: str) -> set[str]:
    return {p.target for p in report.problems if p.code == code and p.target}


@pytest.mark.parametrize("seed", SEEDS)
def test_sound_schemas_are_clean(seed):
    rng = random.Random(seed)
    for _ in range(20):
        assert inspect_schema(_sound_schema(rng)).problems == []


@pytest.mark.parametrize("seed", SEEDS)
def test_cycle_verdict_matches_networkx(seed):
    rng = random.Random(seed)
    for _ in range(30):
        schema = _any_schema(rng)
        fired = any(p.code == "cyclic-foreign-key" for p in inspect_schema(schema).problems)
        assert fired == _nx_has_cycle(schema)


@pytest.mark.parametrize("seed", SEEDS)
def test_orphan_verdict_matches_networkx(seed):
    rng = random.Random(seed)
    for _ in range(30):
        schema = _any_schema(rng)
        assert _targets(inspect_schema(schema), "orphan-table") == _nx_orphans(schema)


@pytest.mark.parametrize("seed", SEEDS)
def test_random_schemas_never_raise(seed):
    rng = random.Random(seed)
    for _ in range(30):
        report = inspect_schema(_any_schema(rng))
        assert isinstance(report.problems, list)


def test_dangling_reference_is_always_an_error():
    schema = Schema(
        tables={"a": {"id": "int"}},
        primary_keys={"a": "id"},
        foreign_keys=[("a.ghost", "nowhere.id")],
        roots=["a"],
        name="dangling",
    )
    assert_fires(inspect_schema(schema), "dangling-foreign-key", ERROR)
