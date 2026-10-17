"""Abnormal input and precedence for the artifact loader.

The loader runs the artifact file, so the interesting cases are the ways a file
can misbehave (missing, syntax error, `sys.exit`, a raise) and the precedence the
discovery rules promise (attribute before builder, first accepted match wins).
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from gxcore.loading import InvalidArtifact, load_from_file, load_module, resolve


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("header", "expected"), [("", int), ("from __future__ import annotations\n", "int")]
)
def test_future_annotations_follow_the_artifact_not_the_loader(tmp_path, header, expected):
    path = _write(tmp_path, "annotation.py", header + "def factory() -> int:\n    return 1\n")
    assert load_module(path).factory.__annotations__["return"] == expected


def test_a_missing_file_is_a_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_module(tmp_path / "nope.py")


def test_a_directory_is_refused_as_a_non_file(tmp_path):
    # A directory named `*.py` used to fall through to an import error. It is not a
    # file at all, which is the same reason a FIFO is refused: `is_file()` is false
    # and reading it either fails or blocks forever.
    with pytest.raises(InvalidArtifact, match="not a regular file"):
        load_module(tmp_path)


def test_a_fifo_is_refused_rather_than_waited_on(tmp_path):
    # Measured: a FIFO named `x.py` blocked the load forever, so a directory run
    # holding one produced no report and no exit code at all.
    fifo = tmp_path / "x.py"
    os.mkfifo(fifo)
    with pytest.raises(InvalidArtifact, match="not a regular file"):
        load_module(fifo)


def test_an_artifact_cannot_end_the_process_behind_the_reporters_back(tmp_path):
    # `os._exit` is not an exception, so `except Exception` never saw it: exit 0 read
    # as "inspected, no error" and 42 read as a code outside the table. The loader
    # traps it while the artifact runs.
    artifact = tmp_path / "x.py"
    artifact.write_text("import os\nos._exit(0)\n", encoding="utf-8")
    with pytest.raises(InvalidArtifact, match=r"os\._exit\(0\)"):
        load_module(artifact)
    # The real function is put back: the next load still works, and `os._exit` is
    # still the one from `os`.
    assert os._exit is not None
    good = tmp_path / "y.py"
    good.write_text("value = 1\n", encoding="utf-8")
    assert load_module(good).value == 1
    assert os._exit.__module__ == "posix" or os._exit.__module__ == "nt"


def test_a_syntax_error_propagates(tmp_path):
    with pytest.raises(SyntaxError):
        load_module(_write(tmp_path, "bad.py", "def (:\n"))


def test_sys_exit_propagates(tmp_path):
    with pytest.raises(SystemExit):
        load_module(_write(tmp_path, "exit.py", "import sys\nsys.exit(7)\n"))


def test_a_runtime_error_propagates(tmp_path):
    with pytest.raises(RuntimeError, match="boom"):
        load_module(_write(tmp_path, "raise.py", "raise RuntimeError('boom')\n"))


def test_two_files_with_the_same_stem_do_not_share_state(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    pa = _write(tmp_path / "a", "m.py", "value = 'A'\n")
    pb = _write(tmp_path / "b", "m.py", "value = 'B'\n")
    assert load_module(pa).value == "A"
    assert load_module(pb).value == "B"
    assert load_module(pa).value == "A"  # and re-loading is still A


def test_resolve_prefers_an_attribute_over_a_builder():
    ns = SimpleNamespace(value=1, build=lambda: 2)
    assert resolve(ns, attrs=("value",), builders=("build",)) == 1


def test_resolve_uses_a_builder_when_the_attribute_is_absent():
    assert resolve(SimpleNamespace(build=lambda: 2), attrs=("value",), builders=("build",)) == 2


def test_resolve_skips_a_none_result():
    ns = SimpleNamespace(build=lambda: None, make=lambda: 3)
    assert resolve(ns, attrs=(), builders=("build", "make")) == 3


def test_resolve_convert_rejects_and_falls_through():
    ns = SimpleNamespace(a=1, b="two")
    got = resolve(
        ns, attrs=("a", "b"), builders=(), convert=lambda v: v if isinstance(v, str) else None
    )
    assert got == "two"


def test_resolve_convert_that_raises_is_treated_as_no_match():
    def convert(_: object) -> object:
        raise ValueError("nope")

    assert resolve(SimpleNamespace(a=1), attrs=("a",), builders=(), convert=convert) is None


def test_resolve_reports_nothing_when_no_attr_or_builder_matches():
    assert resolve(SimpleNamespace(), attrs=("x",), builders=("build",)) is None


def test_a_builder_error_propagates():
    def build() -> object:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        resolve(SimpleNamespace(build=build), attrs=(), builders=("build",))


def test_load_from_file_names_the_description_in_its_error(tmp_path):
    path = _write(tmp_path, "m.py", "x = 1\n")
    with pytest.raises(ValueError, match="no gadget found"):
        load_from_file(path, attrs=("gadget",), builders=(), description="gadget")


def test_same_size_edits_are_not_hidden_by_cached_bytecode(tmp_path):
    import os
    import py_compile

    path = _write(tmp_path, "edited.py", "value = 'A'\n")
    assert load_module(path).value == "A"
    # Another producer may have compiled this file even when this inspector
    # disables bytecode writes. Explicit compilation makes the stale cache real.
    py_compile.compile(str(path), doraise=True)
    stamp = path.stat()
    path.write_text("value = 'B'\n", encoding="utf-8")
    os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    assert load_module(path).value == "B"


def test_a_file_with_no_loadable_suffix_is_an_import_error(tmp_path):
    # `spec_from_file_location` has no loader for a suffix it does not know, which is
    # the branch the directory case used to reach before directories were refused as
    # non-files.
    stray = tmp_path / "x.txt"
    stray.write_text("value = 1\n", encoding="utf-8")
    with pytest.raises(ImportError, match="cannot load a Python module"):
        load_module(stray)
