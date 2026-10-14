"""levelgx branches no example reaches: a blocked start, a bad value, old Pillow."""

from __future__ import annotations

from levelgx import Level
from levelgx.checks import reachable
from levelgx.level import _as_level
from levelgx.render import render_image
from PIL import ImageFont


def test_reachable_is_empty_when_the_start_is_not_passable():
    level = Level(["#####", "#S..#", "#####"])
    assert reachable(level, (0, 0)) == set()  # a wall
    assert reachable(level, (1, 1)) == {(1, 1), (1, 2), (1, 3)}  # floor


def test_as_level_rejects_a_value_that_is_not_a_level():
    assert _as_level("nope") is None
    assert _as_level([]) is None
    assert _as_level(["#S#"]) is not None
    assert _as_level(Level(["#S#"])).rows == ["#S#"]


def test_level_render_survives_a_pillow_without_a_sized_default(monkeypatch):
    real = ImageFont.load_default

    def load_default(*args, **kwargs):
        if args or kwargs:
            raise TypeError("load_default(size=) is new in Pillow 10")
        return real()

    monkeypatch.setattr(ImageFont, "load_default", load_default)
    assert render_image(Level(["#SG#"])).size[0] > 0
