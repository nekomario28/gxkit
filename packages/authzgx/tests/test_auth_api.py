"""The authzgx public helpers and a branch no example exercises."""

from __future__ import annotations

from authzgx import AuthModel, auth_from_parts, inspect_auth
from authzgx.render import image_size
from gxcore.diagram import image_size as node_image_size


def test_auth_from_parts_roundtrips():
    model = auth_from_parts(
        principals=["u"],
        roles=["r"],
        permissions=["p"],
        grants=[("r", "p")],
        assigned=[("u", "r")],
        sensitive=["p"],
        low=["u"],
    )
    assert model.principals == ["u"]
    assert model.grants == [("r", "p")]
    assert model.low == ["u"]


def test_image_size_tracks_the_node_count():
    model = AuthModel(principals=["u"], roles=["r"], permissions=["p"])
    assert image_size(model) == node_image_size(len(model.all_nodes()))


def test_an_undeclared_low_principal_is_skipped():
    model = AuthModel(
        principals=["u"],
        roles=["r"],
        permissions=["p"],
        grants=[("r", "p")],
        sensitive=["p"],
        low=["ghost"],
    )
    assert isinstance(inspect_auth(model).problems, list)


def test_load_model_from_module_level_grants(tmp_path):
    from authzgx import load_model

    src = tmp_path / "a.py"
    src.write_text(
        'GRANTS = [("r", "p")]\n'
        'ROLES = ["r"]\n'
        'PERMISSIONS = ["p"]\n'
        'PRINCIPALS = ["u"]\n'
        'ASSIGNED = [("u", "r")]\n'
        'SENSITIVE = ["p"]\n'
        'LOW = ["u"]\n'
        'NAME = "a"\n'
    )
    model, _module = load_model(src)
    assert model.roles == ["r"]
    assert model.grants == [("r", "p")]


def test_a_dangling_inheritance_is_reported():
    from gxcore import ERROR
    from gxcore.testing import assert_fires

    model = AuthModel(roles=["r"], permissions=["p"], inherits=[("r", "ghost")])
    assert_fires(inspect_auth(model), "dangling-inherit", ERROR)


def test_a_dangling_assignment_is_reported():
    from gxcore import ERROR
    from gxcore.testing import assert_fires

    model = AuthModel(principals=["u"], roles=["r"], permissions=["p"], assigned=[("ghost", "r")])
    assert_fires(inspect_auth(model), "dangling-assignment", ERROR)


def test_a_grant_naming_an_unknown_permission_is_reported():
    from gxcore import ERROR
    from gxcore.testing import assert_fires

    model = AuthModel(roles=["r"], permissions=["p"], grants=[("r", "ghost")])
    assert_fires(inspect_auth(model), "dangling-grant", ERROR)
