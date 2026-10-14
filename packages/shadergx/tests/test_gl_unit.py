"""shadergx's GL helpers, exercised without a GPU by patching moderngl."""

from __future__ import annotations

import pytest
import shadergx.gl as gl
from shadergx.gl import ShaderError, perturb


def test_perturb_covers_each_type():
    assert perturb(True) is False
    assert perturb(3) == 4
    assert perturb(1.5) == pytest.approx(1.87)
    assert perturb([1, 2.0, "x"]) == (1.37, 2.37, "x")


def test_set_returns_false_for_an_unknown_uniform():
    assert gl._set({}, "u", 1) is False


def test_set_returns_true_then_false_from_the_program():
    class Program:
        def __contains__(self, key):
            return True

        def __getitem__(self, key):
            return self

        @property
        def value(self):
            return 0

        @value.setter
        def value(self, v):
            if v == "bad":
                raise TypeError("bad uniform")

    program = Program()
    assert gl._set(program, "u", 1.0) is True
    assert gl._set(program, "u", "bad") is False


def test_context_reports_when_no_backend_works(monkeypatch):
    import moderngl

    def boom(**kwargs):
        if kwargs:
            raise RuntimeError("backend present but no display")
        raise TypeError("default context is unsupported here")

    monkeypatch.setattr(gl, "_ctx", None)
    monkeypatch.setattr(moderngl, "create_standalone_context", boom)
    with pytest.raises(ShaderError):
        gl.context()
