"""framegx branches: the factory, an audio-less volume, no frames, no motion."""

from __future__ import annotations

import shutil
import subprocess

import pytest

pytestmark = pytest.mark.skipif(
    not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
    reason="ffmpeg / ffprobe not installed",
)

from framegx import Video  # noqa: E402
from framegx.checks import inspect_video  # noqa: E402
from framegx.clip import clip  # noqa: E402
from framegx.probe import mean_volume_db  # noqa: E402
from framegx.render import contact_sheet  # noqa: E402


def test_clip_factory_sets_its_fields():
    video = clip("x.mp4", expected_duration=2.0, expect_audio=True, name="c")
    assert (video.path, video.expected_duration, video.expect_audio, video.name) == (
        "x.mp4",
        2.0,
        True,
        "c",
    )


def test_mean_volume_is_none_without_an_audio_track(tmp_path):
    out = tmp_path / "v.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=64x64:rate=5:duration=1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(out),
        ],
        check=True,
    )
    assert mean_volume_db(out) is None


def test_mean_volume_ignores_an_unparseable_line(monkeypatch):
    import importlib

    probe_module = importlib.import_module("framegx.probe")

    class Result:
        returncode = 0
        stderr = "mean_volume: not-a-number dB\n"

    monkeypatch.setattr(probe_module, "_run", lambda *a, **k: Result())
    assert mean_volume_db("x") is None


def test_contact_sheet_says_so_when_there_are_no_frames(tmp_path):
    img = contact_sheet(Video(path=str(tmp_path / "nope.mp4")))
    assert img.size[0] > 0


def test_a_barely_changing_clip_is_reported_as_no_motion(tmp_path):
    out = tmp_path / "dot.mp4"
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x282828:size=160x90:rate=10:duration=2",
            "-vf",
            "drawbox=x='mod(t*80\\,150)':y=40:w=3:h=3:color=white:t=fill",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(out),
        ],
        capture_output=True,
    )
    if result.returncode != 0:
        pytest.skip("libx264 unavailable")
    report = inspect_video(Video(path=str(out)))
    assert any(p.code == "no-motion" for p in report.problems)


def _motion_mp4(tmp_path, name="dotsrc.mp4"):
    out = tmp_path / name
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=160x90:rate=10:duration=2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(out),
        ],
        capture_output=True,
    )
    if result.returncode != 0:
        pytest.skip("libx264 unavailable")
    return out


def test_no_frames_is_reported(monkeypatch, tmp_path):
    import framegx.checks as checks
    import numpy as np

    out = _motion_mp4(tmp_path)
    monkeypatch.setattr(checks, "sample_frames", lambda *a, **k: np.zeros((0, 54, 96), "uint8"))
    report = inspect_video(Video(path=str(out)))
    assert any(p.code == "no-frames" for p in report.problems)


def test_sample_frames_is_empty_when_ffmpeg_returns_nothing(monkeypatch):
    import importlib

    probe_module = importlib.import_module("framegx.probe")

    class Result:
        returncode = 0
        stdout = b""

    monkeypatch.setattr(probe_module, "_run", lambda *a, **k: Result())
    assert probe_module.sample_frames("x").shape[0] == 0


def test_load_video_from_a_module_level_path(tmp_path):
    from framegx import load_video

    src = tmp_path / "clip.py"
    src.write_text('PATH = "out.mp4"\nEXPECTED_DURATION = 3.0\nNAME = "c"\n')
    video, _module = load_video(src)
    assert video.path == "out.mp4"
    assert video.expected_duration == 3.0
    assert video.name == "c"


def test_contact_sheet_survives_a_pillow_without_a_sized_default(monkeypatch, tmp_path):
    from PIL import ImageFont

    real = ImageFont.load_default

    def load_default(*args, **kwargs):
        if args or kwargs:
            raise TypeError("load_default(size=) is new in Pillow 10")
        return real()

    monkeypatch.setattr(ImageFont, "load_default", load_default)
    assert contact_sheet(Video(path=str(tmp_path / "nope.mp4"))).size[0] > 0


def test_probe_tolerates_an_unparseable_duration(monkeypatch):
    import importlib
    import json

    probe_module = importlib.import_module("framegx.probe")
    payload = {
        "streams": [
            {
                "codec_type": "video",
                "width": 10,
                "height": 10,
                "r_frame_rate": "25/1",
                "codec_name": "x",
            }
        ],
        "format": {"duration": "not-a-number"},
    }

    class Result:
        returncode = 0
        stdout = json.dumps(payload)

    monkeypatch.setattr(probe_module, "_run", lambda *a, **k: Result())
    assert probe_module.probe("x")["duration"] is None


def test_a_frame_sampling_failure_is_a_probe_error(monkeypatch, tmp_path):
    import framegx.checks as checks
    from framegx.probe import VideoError

    out = _motion_mp4(tmp_path, "samplefail.mp4")

    def boom(*args, **kwargs):
        raise VideoError("decoder died")

    monkeypatch.setattr(checks, "sample_frames", boom)
    report = inspect_video(Video(path=str(out)))
    assert any(p.code == "probe-error" for p in report.problems)


def test_wrong_fps_and_wrong_size_are_reported(tmp_path):
    from gxcore import WARN

    out = _motion_mp4(tmp_path, "meta.mp4")
    report = inspect_video(Video(path=str(out), expected_fps=99.0, expected_size=(10, 10)))
    codes = {p.code for p in report.problems if p.severity == WARN}
    assert {"wrong-fps", "wrong-size"} <= codes


def test_probe_handles_a_na_rate_and_a_broken_rate(monkeypatch):
    import importlib
    import json

    probe_module = importlib.import_module("framegx.probe")

    def run_with(rate):
        payload = {
            "streams": [
                {
                    "codec_type": "video",
                    "width": 10,
                    "height": 10,
                    "r_frame_rate": rate,
                    "codec_name": "x",
                }
            ],
            "format": {"duration": "1.0"},
        }

        class Result:
            returncode = 0
            stdout = json.dumps(payload)

        monkeypatch.setattr(probe_module, "_run", lambda *a, **k: Result())
        return probe_module.probe("x")

    assert run_with("0/0")["fps"] is None
    assert run_with("1/x")["fps"] is None


def test_probe_reports_output_that_is_not_json(monkeypatch):
    import importlib

    from framegx.probe import VideoError

    probe_module = importlib.import_module("framegx.probe")

    class Result:
        returncode = 0
        stdout = "not json"

    monkeypatch.setattr(probe_module, "_run", lambda *a, **k: Result())
    with pytest.raises(VideoError):
        probe_module.probe("x")
