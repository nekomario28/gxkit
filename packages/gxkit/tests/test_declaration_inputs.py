"""The declaration route: a constant or attribute a tool reads, and refuses.

An earlier review read documents the projects already had; this one read the
declarations an agent writes. The class it found is the worst kind: a *recognised*
declaration whose members are wrong was silently re-shaped — a string became one
name per character, a flag became `bool("no") == True`, a malformed `network` dict
was skipped in favour of another attribute in the same file — and the tool then
reported a verdict about an object the file did not declare. Every case below is one
of those, and the assertion is the tool's own field name.
"""

from __future__ import annotations

import pytest
from gxcore.loading import (
    InvalidArtifact,
    convert_bool,
    convert_mapping,
    convert_names,
    convert_number,
    convert_pairs,
)

# --------------------------------------------------------------------------
# The shared converters: field and index, or nothing.
# --------------------------------------------------------------------------


def test_a_flag_that_is_not_a_flag_is_refused():
    assert convert_bool(True, field="secret") is True
    assert convert_bool(False, field="secret") is False
    for value in ("no", "false", 0, 1, None):
        with pytest.raises(InvalidArtifact, match="secret"):
            convert_bool(value, field="secret")


def test_a_string_is_not_a_list_of_names():
    assert convert_names(["a", "b"], field="MODULES") == ["a", "b"]
    for value in ("ab", 3, None, [1]):
        with pytest.raises(InvalidArtifact, match="MODULES"):
            convert_names(value, field="MODULES")


def test_a_pair_list_keeps_its_arity():
    assert convert_pairs([("a", "b")], field="DEPENDS", arity=2) == [("a", "b")]
    # An element that is not a pair is refused, not exploded into one per character
    # (measured: `GRANTS = ["rp"]` invented a role→permission grant).
    with pytest.raises(InvalidArtifact, match="DEPENDS"):
        convert_pairs(["ab"], field="DEPENDS", arity=2)
    # A fourth element used to be dropped in silence: the transition looked complete.
    for value in ([("a", "b", "e", "extra")], [("a",)], ["ab"], "ab"):
        with pytest.raises(InvalidArtifact, match=r"DEPENDS|TRANSITIONS"):
            convert_pairs(value, field="TRANSITIONS", arity=3)


def test_a_mapping_is_a_mapping():
    assert convert_mapping({"a": "public"}, field="NODES") == {"a": "public"}
    for value in ("AB", [("a",)], None):
        with pytest.raises(InvalidArtifact, match="NODES"):
            convert_mapping(value, field="NODES")


def test_a_number_field_refuses_a_string_and_a_bool():
    assert convert_number(2, field="WIDTH", integer=True) == 2.0
    for value in ("wide", True, None, 1.5):
        with pytest.raises(InvalidArtifact, match="WIDTH"):
            convert_number(value, field="WIDTH", integer=True)


# --------------------------------------------------------------------------
# The declarations themselves, through each tool's loader.
# --------------------------------------------------------------------------


def _module(tmp_path, source: str, name: str = "decl.py"):
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def test_flowgx_refuses_a_state_list_that_is_a_string(tmp_path):
    from flowgx import load_machine

    path = _module(
        tmp_path,
        'STATES = "ab"\nTRANSITIONS = [("a", "b")]\nSTART = "a"\nACCEPT = ["b"]\n',
    )
    with pytest.raises(InvalidArtifact, match="STATES"):
        load_machine(path)


def test_flowgx_refuses_a_transition_with_a_fourth_element(tmp_path):
    from flowgx import load_machine

    path = _module(
        tmp_path,
        'STATES = ["a", "b"]\nTRANSITIONS = [("a", "b", "e", "extra")]\n',
    )
    with pytest.raises(InvalidArtifact, match=r"TRANSITIONS\[0\]"):
        load_machine(path)


def test_protogx_refuses_a_state_list_that_is_a_string(tmp_path):
    from protogx import load_protocol

    path = _module(
        tmp_path,
        'STATES = "ab"\nTRANSITIONS = [("a", "b")]\nMESSAGES = "m"\n',
    )
    with pytest.raises(InvalidArtifact, match="STATES"):
        load_protocol(path)


def test_depsgx_refuses_a_module_list_that_is_a_string(tmp_path):
    from depsgx import load_graph

    path = _module(tmp_path, 'MODULES = "abc"\nDEPENDS = [("a", "b")]\nROOTS = "a"\n')
    with pytest.raises(InvalidArtifact, match=r"MODULES|ROOTS"):
        load_graph(path)


def test_authzgx_refuses_a_grant_list_that_is_a_string(tmp_path):
    from authzgx import load_model

    path = _module(tmp_path, 'GRANTS = ["rp"]\nPRINCIPALS = "u"\nROLES = "r"\n')
    with pytest.raises(InvalidArtifact, match=r"GRANTS|PRINCIPALS|ROLES"):
        load_model(path)


def test_netgx_refuses_a_malformed_network_dict_instead_of_reading_another_attr(tmp_path):
    from netgx import load_network

    # `network` is a *recognised* shape with a string where a mapping belongs. A bare
    # ValueError here let `resolve` fall through to the clean `NETWORK` and report
    # about an object the malformed field never named.
    path = _module(
        tmp_path,
        'network = {"nodes": "ab"}\nNETWORK = {"nodes": {"x": "public"}, "edges": []}\n',
    )
    with pytest.raises(InvalidArtifact, match="nodes"):
        load_network(path)
    # The same shape with the right members still loads.
    ok = _module(tmp_path, 'NETWORK = {"nodes": {"a": "public"}, "edges": [("a", "b")]}\n', "ok.py")
    assert load_network(ok)[0].graph()["a"] == ["b"]


def test_envgx_refuses_a_flag_that_is_a_string(tmp_path):
    from envgx import load_environment

    path = _module(tmp_path, 'VARIABLES = {"TOKEN": {"secret": "no"}}\nREFERENCES = ["TOKEN"]\n')
    with pytest.raises(InvalidArtifact, match="secret"):
        load_environment(path)


def test_seedgx_refuses_a_flag_that_is_a_string(tmp_path):
    from seedgx import load_spec

    path = _module(tmp_path, 'STREAMS = [("a", 1)]\nDETERMINISTIC = "no"\n')
    with pytest.raises(InvalidArtifact, match="DETERMINISTIC"):
        load_spec(path)


def test_framegx_refuses_a_flag_that_is_a_string(tmp_path):
    from framegx import load_video

    path = _module(tmp_path, 'PATH = "tiny.mp4"\nEXPECT_AUDIO = "no"\n')
    with pytest.raises(InvalidArtifact, match="EXPECT_AUDIO"):
        load_video(path)


def test_docgx_refuses_blocks_that_are_not_a_list(tmp_path):
    from docgx import load_page

    path = _module(tmp_path, 'TITLE = "T"\nBLOCKS = "hi"\n')
    with pytest.raises(InvalidArtifact, match="BLOCKS"):
        load_page(path)


def test_docgx_names_the_block_index_when_a_key_is_wrong(tmp_path):
    from docgx import load_page

    path = _module(tmp_path, 'TITLE = "T"\nBLOCKS = [{"text": "hi", "colour": "red"}]\n')
    with pytest.raises(InvalidArtifact, match=r"BLOCKS\[0\]"):
        load_page(path)


def test_chartgx_reports_a_bar_on_a_log_axis_from_the_figure_route(tmp_path):
    """The declared route reported it; the figure route could not see patches."""
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    from chartgx import inspect_figure, load_figure

    path = _module(
        tmp_path,
        "import matplotlib\nmatplotlib.use('Agg')\n"
        "import matplotlib.pyplot as plt\n"
        "fig, ax = plt.subplots()\n"
        "ax.bar(['a'], [0])\n"
        "ax.set_yscale('log')\n",
    )
    figure, _module_object = load_figure(path)
    assert "log-nonpositive" in {problem.code for problem in inspect_figure(figure).problems}


def test_schemagx_does_not_report_orphans_for_a_schema_without_declared_roots(tmp_path):
    """DDL declares no entry points, so the rule that needs them has nothing to apply.

    Measured: the same schema gained `orphan-table: nothing references 'users'` on the
    SQL route and was clean on the Python one.
    """
    from schemagx import inspect_schema, schema_from_ddl

    schema = schema_from_ddl(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT);\n"
        "CREATE TABLE posts (id INTEGER PRIMARY KEY, author_id INTEGER, "
        "FOREIGN KEY (author_id) REFERENCES users (id));\n"
        # A table nothing references and that references nothing *is* what the rule
        # is about — without it the fixture cannot tell the rule apart from silence.
        "CREATE TABLE audit (id INTEGER PRIMARY KEY);\n"
    )
    report = inspect_schema(schema)
    codes = {problem.code for problem in report.problems}
    assert "orphan-table" not in codes, [(p.code, p.message) for p in report.problems]
    # ...and the gap itself is said out loud rather than silently applied.
    notes = [problem for problem in report.problems if problem.code == "not-modelled"]
    assert any("roots" in problem.message for problem in notes), [
        (p.code, p.message) for p in notes
    ]
    assert tmp_path.exists()


def test_apigx_refuses_an_endpoint_that_states_no_method(tmp_path):
    """A declaration states its method; a default invented one.

    Measured: `{"endpoints": [{}]}` inspected as a clean API with one `GET /` endpoint
    the file never named.
    """
    from apigx import load_api

    path = _module(tmp_path, 'api = {"endpoints": [{}]}\n')
    with pytest.raises(InvalidArtifact, match="no 'method'"):
        load_api(path)


def test_chartgx_tolerates_a_patch_it_cannot_measure(tmp_path):
    """A log axis is checked for bars, and not every patch is a bar.

    An annotation patch (a circle, an arrow) has no height; the check skips it rather
    than losing the report.
    """
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    from chartgx import inspect_figure, load_figure

    path = _module(
        tmp_path,
        "import matplotlib\nmatplotlib.use('Agg')\n"
        "import matplotlib.pyplot as plt\n"
        "fig, ax = plt.subplots()\n"
        "ax.set_yscale('log')\n"
        "ax.add_patch(plt.Circle((0.5, 0.5), 0.1))\n",
    )
    figure, _module_object = load_figure(path)
    # The report is produced, and no `log-nonpositive` is claimed about the circle.
    assert "log-nonpositive" not in {p.code for p in inspect_figure(figure).problems}


def test_protogx_transitions_are_two_or_three_names(tmp_path):
    from protogx import load_protocol

    two = _module(
        tmp_path,
        'STATES = ["a", "b"]\nTRANSITIONS = [("a", "b")]\nMESSAGES = ["m"]\nTERMINAL = ["b"]\n',
        "two.py",
    )
    protocol, _module_object = load_protocol(two)
    assert protocol.transitions == [("a", "b")]
    three = _module(
        tmp_path,
        'STATES = ["a", "b"]\nTRANSITIONS = [("a", "b", "m")]\nMESSAGES = ["m"]\n'
        'TERMINAL = ["b"]\n',
        "three.py",
    )
    assert load_protocol(three)[0].transitions == [("a", "b", "m")]
    bad = _module(
        tmp_path,
        'STATES = ["a", "b"]\nTRANSITIONS = [("a", "b", "m", "x")]\nMESSAGES = ["m"]\n',
        "bad.py",
    )
    with pytest.raises(InvalidArtifact, match=r"TRANSITIONS\[0\]"):
        load_protocol(bad)


# --------------------------------------------------------------------------
# A model *built in Python* with a wrong-typed field used to reach the inspector
# and raise a bare TypeError/AttributeError there (13 of them, measured), so the
# refusal belongs where the field is set.
# --------------------------------------------------------------------------

BUILDERS = {
    "crongx.start": (
        lambda: __import__("crongx").Schedule(
            runs=[__import__("crongx").Run("a", "oops", 1, "cpu")]
        ),
        "start",
    ),
    "crongx.duration": (
        lambda: __import__("crongx").Schedule(runs=[__import__("crongx").Run("a", 0, "x", "cpu")]),
        "duration",
    ),
    "apigx.method": (
        lambda: __import__("apigx").API(endpoints=[__import__("apigx").Endpoint(200, "/x")]),
        "method",
    ),
    "apigx.statuses": (
        lambda: __import__("apigx").API(
            endpoints=[__import__("apigx").Endpoint("GET", "/x", statuses=[1.5])]
        ),
        "statuses",
    ),
    "protogx.transitions": (
        lambda: __import__("protogx").Protocol(states=["a", "b"], transitions=[("a",)]),
        "transitions",
    ),
    "apigx.path": (
        lambda: __import__("apigx").API(endpoints=[__import__("apigx").Endpoint("GET", 7)]),
        "path",
    ),
    "authzgx.assigned": (
        lambda: __import__("authzgx").AuthModel(
            principals=["u"], roles=["r"], assigned=[("u", "r", "x")]
        ),
        "assigned",
    ),
    "depsgx.layers": (
        lambda: __import__("depsgx").ModuleGraph(modules=["a"], depends=[], layers=[7]),
        "layers",
    ),
    "flowgx.states": (
        lambda: __import__("flowgx").Machine(states=[7], transitions=[("a", "b")]),
        "states",
    ),
    "flowgx.transitions": (
        lambda: __import__("flowgx").Machine(states=["a", "b"], transitions=[("a",)]),
        "transitions",
    ),
    "flowgx.accept": (
        lambda: __import__("flowgx").Machine(states=["a"], transitions=[], accept=[7]),
        "accept",
    ),
    "protogx.responses": (
        lambda: __import__("protogx").Protocol(states=["a"], transitions=[], responses=["x"]),
        "responses",
    ),
    "schemagx.foreign_keys": (
        lambda: __import__("schemagx").Schema(tables={"a": {"id": "int"}}, foreign_keys=["a.id"]),
        "foreign_keys",
    ),
    "schemagx.roots": (
        lambda: __import__("schemagx").Schema(tables={"a": {"id": "int"}}, roots=[7]),
        "roots",
    ),
    "pipegx.steps": (lambda: __import__("pipegx").Pipeline(steps=[7]), "steps"),
    "pipegx.goals": (
        lambda: __import__("pipegx").Pipeline(steps=[__import__("pipegx").Step("a")], goals=[7]),
        "goals",
    ),
    "levelgx.rows": (lambda: __import__("levelgx").Level(rows=[7]), "rows"),
    "docgx.blocks": (
        lambda: __import__("docgx").Page(title="t", blocks=[7]),
        "blocks",
    ),
    "docgx.x": (
        lambda: __import__("docgx").Page(
            title="t", blocks=[__import__("docgx").Block("t", x="left")]
        ),
        "x",
    ),
    "docgx.width": (
        lambda: __import__("docgx").Page(title="t", width="wide", blocks=[]),
        "width",
    ),
    "shadergx.size": (
        lambda: __import__("shadergx").Shader(fragment="void main(){}", size=("a", "b")),
        "size",
    ),
    "shadergx.uniforms": (
        lambda: __import__("shadergx").Shader(fragment="void main(){}", uniforms=["u"]),
        "uniforms",
    ),
    "framegx.expected_duration": (
        lambda: __import__("framegx").Video("x.mp4", expected_duration="2.0"),
        "expected_duration",
    ),
    "framegx.sample_fps": (
        lambda: __import__("framegx").Video("x.mp4", sample_fps="2"),
        "sample_fps",
    ),
}


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_a_model_built_with_a_wrong_typed_field_is_refused_where_it_is_set(name):
    build, field = BUILDERS[name]
    with pytest.raises(InvalidArtifact, match=field):
        build()


def test_a_value_the_tool_has_a_finding_for_is_not_refused_at_construction():
    """Type errors are refused at the field; *values* are the checks' business.

    `Stream("bad", 0.5)` must reach `inspect_spec` to be reported as `invalid-seed` (the
    whole point of making that code reachable), and a NaN time is `non-finite-time`, so
    validating the values here would take those findings away.
    """
    from seedgx import SeedSpec, Stream, inspect_spec

    report = inspect_spec(SeedSpec(streams=[Stream("bad", 0.5)]))
    assert "invalid-seed" in {problem.code for problem in report.problems}
    from crongx import Run, Schedule, inspect_schedule

    assert "non-finite-time" in {
        problem.code
        for problem in inspect_schedule(Schedule(runs=[Run("a", float("nan"), 1, "cpu")])).problems
    }
