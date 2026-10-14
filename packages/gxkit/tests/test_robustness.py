"""Robustness: a broken or weird artifact must never traceback, and `inspect`
must not raise on odd (but well-formed) input.

Two guards:
  * every tool, fed a malformed file, exits 2 with a message (not a traceback);
  * the analysis of random-but-valid artifacts returns a Report instead of
    raising (off-by-one and empty-input bugs live here).
"""

from __future__ import annotations

import importlib
import random

import pytest

from gxcore import Report
from gxcore.cli import run

TOOL_NAMES = ["chartgx", "levelgx", "flowgx", "protogx", "authzgx",
              "depsgx", "schemagx", "docgx", "shadergx", "framegx"]

MALFORMED = {
    "empty": "",
    "syntax-error": "def (:\n",
    "not-an-artifact": "x = 1\n",
    "exits-while-loading": "import sys\nsys.exit(3)\n",
    "raises-while-loading": "raise RuntimeError('boom')\n",
}


def _tool(name: str):
    return importlib.import_module(f"{name}.tool").TOOL


@pytest.mark.parametrize("name", TOOL_NAMES)
@pytest.mark.parametrize("kind", list(MALFORMED))
def test_malformed_input_exits_2_not_traceback(tmp_path, capsys, name, kind):
    path = tmp_path / "artifact.py"
    path.write_text(MALFORMED[kind])
    rc = run(_tool(name), ["inspect", str(path), "--no-storyboard"])
    captured = capsys.readouterr()
    assert rc == 2, f"{name}/{kind}: exit {rc}, stderr={captured.err!r}"
    assert "Traceback" not in captured.err


# --------------------------------------------------------------------------- #
# property test: random well-formed artifacts must not raise
# --------------------------------------------------------------------------- #

CELLS = "#.SGX!><^v "


def _random_levels(rng):
    from levelgx import Level

    for _ in range(40):
        h, w = rng.randint(1, 6), rng.randint(1, 6)
        rows = ["".join(rng.choice(CELLS) for _ in range(w)) for _ in range(h)]
        yield Level(rows)


def _random_machines(rng):
    from flowgx import Machine

    for _ in range(40):
        n = rng.randint(0, 5)
        states = [f"s{i}" for i in range(n)]
        edges = [(rng.choice(states), rng.choice(states)) for _ in range(rng.randint(0, 6))] if states else []
        yield Machine(states=states, start=(states[0] if states else None),
                      accept=[states[0]] if states else [], transitions=edges)


def _random_protocols(rng):
    from protogx import Protocol

    for _ in range(40):
        n = rng.randint(0, 5)
        states = [f"s{i}" for i in range(n)]
        msgs = [f"m{i}" for i in range(rng.randint(0, 4))]
        edges = []
        for _ in range(rng.randint(0, 6)):
            if states:
                edges.append((rng.choice(states), rng.choice(states), rng.choice(msgs) if msgs else None))
        yield Protocol(states=states, start=(states[0] if states else None),
                       terminal=[states[0]] if states else [], messages=msgs,
                       transitions=[e for e in edges if e[2] is not None])


def _random_auths(rng):
    from authzgx import AuthModel

    for _ in range(40):
        roles = [f"r{i}" for i in range(rng.randint(0, 4))]
        perms = [f"p{i}" for i in range(rng.randint(0, 4))]
        principals = [f"u{i}" for i in range(rng.randint(0, 3))]
        yield AuthModel(
            principals=principals, roles=roles, permissions=perms,
            grants=[(rng.choice(roles), rng.choice(perms)) for _ in range(rng.randint(0, 5))] if roles and perms else [],
            inherits=[(rng.choice(roles), rng.choice(roles)) for _ in range(rng.randint(0, 4))] if roles else [],
            assigned=[(rng.choice(principals), rng.choice(roles)) for _ in range(rng.randint(0, 4))] if principals and roles else [],
            sensitive=perms[:1], low=principals[:1])


def _random_deps(rng):
    from depsgx import ModuleGraph

    for _ in range(40):
        modules = [f"m{i}" for i in range(rng.randint(0, 5))]
        yield ModuleGraph(
            modules=modules,
            depends=[(rng.choice(modules), rng.choice(modules)) for _ in range(rng.randint(0, 5))] if modules else [],
            roots=modules[:1],
            layers=[[m] for m in modules] if rng.random() < 0.5 else [])


def _random_schemas(rng):
    from schemagx import Schema

    for _ in range(40):
        tables = {f"t{i}": {"id": "int"} for i in range(rng.randint(0, 4))}
        names = list(tables)
        fks = [(f"{rng.choice(names)}.id", f"{rng.choice(names)}.id") for _ in range(rng.randint(0, 5))] if names else []
        yield Schema(tables=tables, primary_keys={n: "id" for n in names}, foreign_keys=fks, roots=names[:1])


def _random_pages(rng):
    from docgx import Block, Page

    for _ in range(40):
        blocks = [Block("word " * rng.randint(0, 40), x=rng.random(), y=rng.random(),
                        font_size=rng.randint(4, 40)) for _ in range(rng.randint(0, 4))]
        yield Page(width=rng.choice([320, 640, 1280]), height=rng.choice([240, 480, 720]),
                   title=rng.choice(["", "T"]), blocks=blocks)


GENERATORS = {
    "levelgx": _random_levels,
    "flowgx": _random_machines,
    "protogx": _random_protocols,
    "authzgx": _random_auths,
    "depsgx": _random_deps,
    "schemagx": _random_schemas,
    "docgx": _random_pages,
}

INSPECT = {
    "levelgx": "inspect_level",
    "flowgx": "inspect_machine",
    "protogx": "inspect_protocol",
    "authzgx": "inspect_auth",
    "depsgx": "inspect_graph",
    "schemagx": "inspect_schema",
    "docgx": "inspect_page",
}


@pytest.mark.parametrize("name", list(GENERATORS))
def test_random_artifacts_do_not_raise(name):
    inspect = getattr(importlib.import_module(name), INSPECT[name])
    rng = random.Random(20261014)
    for artifact in GENERATORS[name](rng):
        report = inspect(artifact)
        assert isinstance(report, Report)


def test_weird_chart_figures_do_not_raise():
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    from chartgx import inspect_figure

    figures = []
    for build in (
        lambda ax: None,                                    # empty axes
        lambda ax: ax.plot([1], [float("nan")]),            # NaN
        lambda ax: ax.bar(["a"], [0.0]),                    # zero-height bar
        lambda ax: ax.plot([1, 2, 3], [1, 1, 1]),           # constant
        lambda ax: [ax.plot([0, 1], [i, i + 1]) for i in range(50)],  # many series
        lambda ax: ax.set_yscale("log") or ax.plot([1, 2], [0, 5]),   # log + zero
    ):
        plt.close("all")
        fig, ax = plt.subplots()
        build(ax)
        figures.append(fig)
    for fig in figures:
        assert isinstance(inspect_figure(fig), Report)
