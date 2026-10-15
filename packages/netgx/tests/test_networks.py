"""Prove every netgx check fires on a topology that has the fault and stays quiet otherwise."""

from __future__ import annotations

from pathlib import Path

from gxcore import ERROR, INFO, WARN
from gxcore.testing import assert_fires, assert_quiet
from netgx import Network, inspect_network, load_network, network_from_parts


def _net(**kw):
    base = {
        "nodes": {
            "internet": "public",
            "web": "service",
            "admin": "service",
            "db": "data",
        },
        "edges": [("internet", "web"), ("admin", "db")],
        "sensitive": ["db"],
    }
    base.update(kw)
    return Network(**base)


def test_a_segmented_network_has_no_problems():
    assert inspect_network(_net()).problems == []


def test_dangling_edge():
    assert_fires(inspect_network(_net(edges=[("web", "ghost")])), "dangling-edge", ERROR)


def test_a_dangling_edge_identity_names_its_edge_and_endpoint():
    report = inspect_network(_net(edges=[("web", "ghost")]))
    dangling = [p for p in report.problems if p.code == "dangling-edge"]
    assert [p.identity for p in dangling] == [("web", "ghost", "ghost")]


def test_two_dangling_endpoints_on_one_edge_are_two_findings():
    report = inspect_network(
        Network(nodes={"a": "service"}, edges=[("a", "missing"), ("missing", "a")])
    )
    dangling = [p for p in report.problems if p.code == "dangling-edge"]
    assert len(dangling) == 2
    assert {p.identity for p in dangling} == {
        ("a", "missing", "missing"),
        ("missing", "a", "missing"),
    }


def test_public_reaches_sensitive():
    assert_fires(
        inspect_network(_net(edges=[("internet", "web"), ("web", "db")])),
        "public-reaches-sensitive",
        ERROR,
    )


def test_a_private_path_to_sensitive_is_quiet():
    net = _net(
        nodes={"internet": "public", "admin": "service", "db": "data"},
        edges=[("admin", "db")],
    )
    assert_quiet(inspect_network(net), "public-reaches-sensitive")


def test_self_loop():
    assert_fires(inspect_network(_net(edges=[("web", "web")])), "self-loop", WARN)


def test_duplicate_edge():
    assert_fires(
        inspect_network(_net(edges=[("internet", "web"), ("internet", "web")])),
        "duplicate-edge",
        INFO,
    )


def test_isolated_node():
    net = _net(nodes={"internet": "public", "web": "service", "lonely": "data"})
    assert_fires(inspect_network(net), "isolated-node", INFO)


def test_no_public():
    net = _net(nodes={"web": "service", "db": "data"})
    assert_fires(inspect_network(net), "no-public", INFO)


def test_network_from_parts_roundtrips():
    net = network_from_parts(nodes={"a": "public"}, edges=[("a", "b")], name="x")
    assert net.names() == ["a"] and net.graph()["a"] == ["b"] and net.name == "x"


def test_loader_accepts_nodes_and_edges(tmp_path):
    src = tmp_path / "n.py"
    src.write_text('NODES = {"a": "public", "b": "data"}\nEDGES = [("a", "b")]\nNAME = "x"\n')
    net, _module = load_network(src)
    assert net.names() == ["a", "b"]
    assert net.name == "x"


def test_loader_accepts_a_dict(tmp_path):
    src = tmp_path / "n.py"
    src.write_text('NETWORK = {"nodes": {"a": "public"}, "edges": [("a", "b")]}\n')
    net, _module = load_network(src)
    assert net.graph()["a"] == ["b"]


def test_converters():
    from netgx.model import _as_network

    net = Network(nodes={"a": "public"})
    assert _as_network(net) is net
    assert _as_network(42) is None


def test_image_size_tracks_the_node_count():
    from netgx.render import image_size

    assert image_size(_net())[0] > 0


def test_examples_load_and_are_diagnosed():
    examples = Path(__file__).resolve().parents[1] / "examples"
    good, _ = load_network(examples / "good_network.py")
    broken, _ = load_network(examples / "broken_network.py")
    assert inspect_network(good).errors == 0
    report = inspect_network(broken)
    for code, severity in (
        ("dangling-edge", ERROR),
        ("public-reaches-sensitive", ERROR),
        ("self-loop", WARN),
        ("duplicate-edge", INFO),
    ):
        assert_fires(report, code, severity)
