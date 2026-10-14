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

from gxcore import ERROR, WARN  # noqa: E402
from gxcore.testing import assert_fires, assert_quiet  # noqa: E402
from framegx import Video, inspect_video, load_video  # noqa: E402


def make(tmp_path: Path, source: str, name: str = "v.mp4") -> Video:
    out = tmp_path / name
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", source,
         "-pix_fmt", "yuv420p", str(out)],
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
