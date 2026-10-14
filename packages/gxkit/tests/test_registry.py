"""The catalogue and the dispatcher."""

from __future__ import annotations

from types import SimpleNamespace

from gxkit import TOOLS, detect
from gxkit.cli import main

# --------------------------------------------------------------------------- #
# registry
# --------------------------------------------------------------------------- #


def test_catalogue_covers_every_tool():
    import pathlib

    packages = pathlib.Path(__file__).resolve().parents[2]
    expected = sorted(
        d.name
        for d in packages.iterdir()
        if (d / "pyproject.toml").exists() and d.name not in {"gxcore", "gxkit"}
    )
    assert sorted(t.name for t in TOOLS) == expected


def test_detect_by_object_class():
    class Machine: ...

    class Protocol: ...

    class Level: ...

    class AuthModel: ...

    class ModuleGraph: ...

    class Schema: ...

    class Page: ...

    class Shader: ...

    class Video: ...

    class Figure: ...

    assert detect(SimpleNamespace(machine=Machine())).name == "flowgx"
    assert detect(SimpleNamespace(protocol=Protocol())).name == "protogx"
    assert detect(SimpleNamespace(level=Level())).name == "levelgx"
    assert detect(SimpleNamespace(model=AuthModel())).name == "authzgx"
    assert detect(SimpleNamespace(graph=ModuleGraph())).name == "depsgx"
    assert detect(SimpleNamespace(schema=Schema())).name == "schemagx"
    assert detect(SimpleNamespace(page=Page())).name == "docgx"
    assert detect(SimpleNamespace(shader=Shader())).name == "shadergx"
    assert detect(SimpleNamespace(video=Video())).name == "framegx"
    assert detect(SimpleNamespace(fig=Figure())).name == "chartgx"


def test_detect_by_marker():
    assert detect(SimpleNamespace(rows=["###", "#S#"])).name == "levelgx"
    assert detect(SimpleNamespace(GRANTS=[("r", "p")], ROLES=["r"])).name == "authzgx"
    assert detect(SimpleNamespace(DEPENDS=[("a", "b")])).name == "depsgx"
    assert detect(SimpleNamespace(FOREIGN_KEYS=[("a.b", "c.d")])).name == "schemagx"
    assert detect(SimpleNamespace(BLOCKS=[], TITLE="t")).name == "docgx"
    assert detect(SimpleNamespace(FRAGMENT="void main(){}")).name == "shadergx"
    assert detect(SimpleNamespace(PATH="out.mp4")).name == "framegx"
    # a protocol file also has STATES/TRANSITIONS; MESSAGES must win
    assert (
        detect(SimpleNamespace(STATES=["a"], TRANSITIONS=[("a", "a")], MESSAGES=["SYN"])).name
        == "protogx"
    )


def test_detect_unknown_is_none():
    assert detect(SimpleNamespace(hello="world")) is None


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #


def test_tools_lists_the_catalogue(capsys):
    assert main(["tools"]) == 0
    out = capsys.readouterr().out
    for name in ("chartgx", "levelgx", "framegx"):
        assert name in out


def test_tools_json(capsys):
    import json

    assert main(["tools", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert {"name", "inspects"} == set(data[0])


def test_inspect_routes_and_returns_the_tools_code(capsys):
    # the levelgx soft-lock example must route to levelgx and exit 1
    example = (
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / "levelgx"
        / "examples"
        / "softlock_level.py"
    )
    rc = main(["inspect", str(example), "--no-storyboard"])
    assert rc == 1
    assert "levelgx" in capsys.readouterr().err


def test_inspect_explicit_unknown_tool_exits_2(tmp_path, capsys):
    src = tmp_path / "x.py"
    src.write_text("x = 1\n")
    assert main(["inspect", "nope", str(src)]) == 2
    assert "unknown tool" in capsys.readouterr().err


def test_inspect_a_tool_without_a_file_exits_2(capsys):
    assert main(["inspect", "levelgx"]) == 2
    assert "needs a file" in capsys.readouterr().err


def test_inspect_two_files_with_json_is_refused(tmp_path, capsys):
    a = tmp_path / "a.py"
    a.write_text("x = 1\n")
    b = tmp_path / "b.py"
    b.write_text("y = 1\n")
    assert main(["inspect", str(a), str(b), "--json"]) == 2
    assert "single artifact" in capsys.readouterr().err


def test_inspect_undetectable_exits_2(tmp_path, capsys):
    src = tmp_path / "x.py"
    src.write_text("hello = 1\n")
    assert main(["inspect", str(src)]) == 2
    assert "could not tell" in capsys.readouterr().err


def test_inspect_a_directory_runs_each_artifact(capsys):
    examples = __import__("pathlib").Path(__file__).resolve().parents[2] / "levelgx" / "examples"
    rc = main(["inspect", str(examples), "--no-storyboard"])
    assert rc == 1  # the soft-lock example is in there
    assert "levelgx" in capsys.readouterr().err


def test_inspect_empty_directory_exits_2(tmp_path, capsys):
    assert main(["inspect", str(tmp_path)]) == 2
    assert "no *.py artifacts" in capsys.readouterr().err
