"""Prove every framegx check fires on a render that has the fault.

Videos are generated with ffmpeg into a temp directory, so the tests need no
committed media and skip cleanly where ffmpeg is absent.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
    reason="ffmpeg / ffprobe not installed",
)

from framegx import Video, inspect_video, load_video  # noqa: E402
from gxcore import ERROR, WARN  # noqa: E402
from gxcore.testing import assert_fires, assert_quiet  # noqa: E402


def make(tmp_path: Path, source: str, name: str = "v.mp4") -> Video:
    out = tmp_path / name
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            source,
            "-pix_fmt",
            "yuv420p",
            str(out),
        ],
        check=True,
    )
    return Video(path=str(out), name="v")


def test_a_moving_render_is_clean(tmp_path):
    video = make(tmp_path, "testsrc=size=160x90:rate=10:duration=2")
    report = inspect_video(video)
    assert report.errors == 0
    assert_quiet(report, "frozen")
    assert_quiet(report, "all-black")


def test_black_frame(tmp_path):
    video = make(tmp_path, "color=c=black:size=160x90:rate=10:duration=2")
    assert_fires(inspect_video(video), "all-black", ERROR)


def test_frozen_picture(tmp_path):
    video = make(tmp_path, "color=c=navy:size=160x90:rate=10:duration=3")
    assert_fires(inspect_video(video), "frozen", ERROR)


def test_duration_mismatch(tmp_path):
    video = make(tmp_path, "testsrc=size=160x90:rate=10:duration=2")
    video.expected_duration = 5.0
    assert_fires(inspect_video(video), "duration-mismatch", WARN)


def test_missing_audio(tmp_path):
    video = make(tmp_path, "testsrc=size=160x90:rate=10:duration=2")
    video.expect_audio = True
    assert_fires(inspect_video(video), "no-audio", WARN)


def test_missing_file(tmp_path):
    assert_fires(inspect_video(Video(path=str(tmp_path / "nope.mp4"))), "missing-file", ERROR)


def test_examples_load_and_are_diagnosed():
    examples = Path(__file__).resolve().parents[1] / "examples"
    good, _ = load_video(examples / "good_clip.py")
    frozen, _ = load_video(examples / "frozen_clip.py")
    assert good.resolved_path and good.resolved_path.exists()
    assert inspect_video(good).errors == 0
    assert_fires(inspect_video(frozen), "frozen", ERROR)


def test_a_missing_program_refuses_instead_of_reporting_a_finding(monkeypatch, tmp_path):
    """`MissingCapability` escapes; a plain `VideoError` is the finding.

    A missing `ffprobe` is not a fault in the artifact, so reporting it as
    `probe-error` would send the caller to fix a clip that is fine. All three places
    are exercised *in process*: the coverage floor counts what runs here, and a
    re-raise that only a subprocess reaches is invisible to it.
    """
    import importlib

    from framegx.probe import MissingCapability

    # `framegx` exports a *function* named `checks`, so the submodule is fetched by
    # name — `from framegx import checks` would give the function.
    checks = importlib.import_module("framegx.checks")
    probe_module = importlib.import_module("framegx.probe")

    def refuse(*_args: object, **_kwargs: object):
        raise MissingCapability("ffprobe is not installed or not on PATH")

    # 1. The program is genuinely absent: an ordinary subprocess with no PATH.
    media = tmp_path / "present.mp4"
    media.write_bytes(b"not really a video")
    monkeypatch.setenv("PATH", "")
    with pytest.raises(MissingCapability):
        probe_module.probe(media)
    monkeypatch.undo()

    # 2. The first call site: reading metadata.
    # The file has to exist — `inspect_video` reports `missing-file` and returns
    # before it ever probes, which is how the first version of this test passed for
    # the wrong reason.
    monkeypatch.setattr(checks, "probe", refuse)
    with pytest.raises(MissingCapability):
        checks.inspect_video(Video(path=str(media)))
    monkeypatch.undo()

    # 3. The second call site: sampling frames, with a probe that works.
    examples = Path(__file__).resolve().parents[1] / "examples"
    real, _module = load_video(examples / "frozen_clip.py")
    monkeypatch.setattr(checks, "sample_frames", refuse)
    with pytest.raises(MissingCapability):
        checks.inspect_video(real)
