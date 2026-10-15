"""Prove every seedgx check fires on a manifest that has the fault and stays quiet otherwise."""

from __future__ import annotations

from pathlib import Path

import pytest
from gxcore import ERROR, INFO, WARN
from gxcore.loading import InvalidArtifact
from gxcore.testing import assert_fires, assert_quiet
from seedgx import SeedSpec, Stream, inspect_spec, load_spec, spec_from_parts


def test_a_clean_manifest_has_no_problems():
    spec = SeedSpec(streams=[Stream("python", 42), Stream("numpy", 7)])
    assert inspect_spec(spec).problems == []


def test_direct_inspection_also_rejects_a_noninteger_seed():
    assert_fires(inspect_spec(SeedSpec(streams=[Stream("bad", 0.5)])), "invalid-seed", ERROR)


def test_missing_seed():
    assert_fires(inspect_spec(SeedSpec(streams=[Stream("numpy", None)])), "missing-seed", ERROR)


def test_duplicate_stream():
    spec = SeedSpec(streams=[Stream("torch", 1), Stream("torch", 2)])
    assert_fires(inspect_spec(spec), "duplicate-stream", ERROR)


def test_seed_out_of_range():
    spec = SeedSpec(streams=[Stream("jax", 2**32)])
    assert_fires(inspect_spec(spec), "seed-out-of-range", ERROR)
    assert_fires(inspect_spec(SeedSpec(streams=[Stream("jax", -1)])), "seed-out-of-range", ERROR)


def test_duplicate_seed():
    spec = SeedSpec(streams=[Stream("python", 42), Stream("numpy", 42)])
    assert_fires(inspect_spec(spec), "duplicate-seed", WARN)


def test_distinct_seeds_are_quiet():
    spec = SeedSpec(streams=[Stream("python", 42), Stream("numpy", 7)])
    assert_quiet(inspect_spec(spec), "duplicate-seed")


def test_non_deterministic():
    assert_fires(
        inspect_spec(SeedSpec(streams=[Stream("python", 1)], deterministic=False)),
        "non-deterministic",
        INFO,
    )


def test_no_streams():
    assert_fires(inspect_spec(SeedSpec()), "no-streams", INFO)


def test_spec_from_parts_roundtrips():
    spec = spec_from_parts(streams=[Stream("python", 1)], name="x")
    assert spec.names() == ["python"] and spec.name == "x"


def test_loader_accepts_streams(tmp_path):
    src = tmp_path / "s.py"
    src.write_text('STREAMS = [("python", 42), ("numpy", 7)]\nNAME = "x"\n')
    spec, _module = load_spec(src)
    assert spec.names() == ["python", "numpy"]
    assert spec.name == "x"


def test_loader_accepts_a_dict(tmp_path):
    src = tmp_path / "s.py"
    src.write_text('SEED = {"streams": [{"name": "python", "seed": 1}], "deterministic": False}\n')
    spec, _module = load_spec(src)
    assert spec.streams[0].seed == 1
    assert spec.deterministic is False


def test_converters():
    from seedgx.model import _as_spec, _as_stream

    stream = Stream("python", 1)
    assert _as_stream(stream) is stream
    assert _as_stream("python").name == "python"
    assert _as_stream({"name": "python", "seed": 2}).seed == 2
    assert _as_stream(("python", 3)).seed == 3
    assert _as_stream({"seed": 1}) is None
    assert _as_stream(42) is None
    spec = SeedSpec(streams=[stream])
    assert _as_spec(spec) is spec
    assert _as_spec([("python", 1)]) is not None
    with pytest.raises(InvalidArtifact, match=r"streams\[0\]"):
        _as_spec([42])
    with pytest.raises(InvalidArtifact, match=r"streams\[0\]"):
        _as_spec({"streams": [42]})
    assert _as_spec(42) is None


def test_image_size_tracks_the_stream_count():
    from seedgx.render import image_size

    assert image_size(SeedSpec(streams=[Stream("python", 1)]))[0] > 0


def test_examples_load_and_are_diagnosed():
    examples = Path(__file__).resolve().parents[1] / "examples"
    good, _ = load_spec(examples / "good_seed.py")
    broken, _ = load_spec(examples / "broken_seed.py")
    assert inspect_spec(good).errors == 0
    report = inspect_spec(broken)
    for code, severity in (
        ("missing-seed", ERROR),
        ("seed-out-of-range", ERROR),
        ("duplicate-stream", ERROR),
        ("duplicate-seed", WARN),
        ("non-deterministic", INFO),
    ):
        assert_fires(report, code, severity)
