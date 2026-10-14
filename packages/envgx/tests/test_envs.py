"""Prove every envgx check fires on a config that has the fault and stays quiet otherwise."""

from __future__ import annotations

from pathlib import Path

from envgx import (
    Environment,
    Variable,
    environment_from_parts,
    inspect_environment,
    load_environment,
)
from gxcore import ERROR, INFO, WARN
from gxcore.testing import assert_fires, assert_quiet


def _env(**kw):
    base = {
        "variables": [
            Variable("DATABASE_URL", required=True, secret=True),
            Variable("PORT", default="8080"),
        ],
        "references": ["DATABASE_URL", "PORT"],
    }
    base.update(kw)
    return Environment(**base)


def test_a_clean_environment_has_no_problems():
    assert inspect_environment(_env()).problems == []


def test_empty_name():
    assert_fires(
        inspect_environment(_env(variables=[Variable("")], references=[])), "empty-name", ERROR
    )


def test_duplicate_variable():
    env = _env(variables=[Variable("PORT"), Variable("PORT")])
    assert_fires(inspect_environment(env), "duplicate-variable", ERROR)


def test_unknown_type():
    assert_fires(
        inspect_environment(_env(variables=[Variable("PORT", type="integer")])),
        "unknown-type",
        ERROR,
    )


def test_secret_with_default():
    env = _env(variables=[Variable("TOKEN", secret=True, default="x")], references=["TOKEN"])
    assert_fires(inspect_environment(env), "secret-with-default", ERROR)


def test_required_with_default():
    env = _env(variables=[Variable("PORT", required=True, default="8080")], references=["PORT"])
    assert_fires(inspect_environment(env), "required-with-default", WARN)


def test_undeclared_reference():
    assert_fires(inspect_environment(_env(references=["MISSING"])), "undeclared-reference", ERROR)


def test_unused_variable():
    env = _env(variables=[Variable("PORT"), Variable("DEBUG")], references=["PORT"])
    assert_fires(inspect_environment(env), "unused-variable", INFO)


def test_used_variables_are_quiet():
    assert_quiet(
        inspect_environment(_env(variables=[Variable("PORT")], references=["PORT"])),
        "unused-variable",
    )


def test_no_variables():
    assert_fires(inspect_environment(Environment()), "no-variables", INFO)


def test_environment_from_parts_roundtrips():
    env = environment_from_parts(variables=[Variable("PORT")], references=["PORT"], name="x")
    assert env.names() == ["PORT"] and env.name == "x"


def test_loader_accepts_a_variables_mapping(tmp_path):
    src = tmp_path / "e.py"
    src.write_text(
        'VARIABLES = {"PORT": {"type": "int", "default": "8080"}}\nREFERENCES = ["PORT"]\nNAME = "x"\n'
    )
    env, _module = load_environment(src)
    assert env.variables[0].type == "int"
    assert env.name == "x"


def test_loader_accepts_a_list(tmp_path):
    src = tmp_path / "e.py"
    src.write_text('ENV = [{"name": "PORT", "type": "int"}]\n')
    env, _module = load_environment(src)
    assert env.names() == ["PORT"]


def test_converters():
    from envgx.model import _as_environment, _as_variable

    env = Environment(variables=[Variable("PORT")])
    assert _as_environment(env) is env
    assert _as_environment(42) is None
    assert _as_variable(Variable("PORT")).name == "PORT"
    assert _as_variable("PORT").name == "PORT"
    assert _as_variable({"name": "PORT", "type": "int"}).type == "int"
    assert _as_variable(42) is None


def test_image_size_tracks_the_variable_count():
    from envgx.render import image_size

    assert image_size(_env())[0] > 0


def test_examples_load_and_are_diagnosed():
    examples = Path(__file__).resolve().parents[1] / "examples"
    good, _ = load_environment(examples / "good_env.py")
    broken, _ = load_environment(examples / "broken_env.py")
    assert inspect_environment(good).errors == 0
    report = inspect_environment(broken)
    for code, severity in (
        ("secret-with-default", ERROR),
        ("unknown-type", ERROR),
        ("duplicate-variable", ERROR),
        ("undeclared-reference", ERROR),
        ("required-with-default", WARN),
        ("unused-variable", INFO),
    ):
        assert_fires(report, code, severity)


def test_converters_cover_every_shape():
    from envgx.model import _as_environment, _as_variable

    assert _as_environment(Environment(variables=[Variable("PORT")])) is not None
    assert _as_environment({"variables": [{"name": "PORT"}]}) is not None
    assert _as_environment({"variables": [42]}) is None
    assert _as_environment([Variable("PORT")]) is not None
    assert _as_environment([42]) is None
    assert _as_variable({"type": "int"}) is None
    assert _as_variable(42) is None


def test_loader_accepts_bare_specs(tmp_path):
    src = tmp_path / "e.py"
    src.write_text('VARIABLES = {"PORT": None, "DEBUG": "bool"}\n')
    env, _module = load_environment(src)
    assert env.names() == ["PORT", "DEBUG"]
