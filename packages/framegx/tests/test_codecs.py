"""Inspect more than one container/codec.

`framegx` shells out to ffmpeg, so the file it is handed can be H.264 in MP4, VP9
in WebM, Theora, a GIF, or something with an audio track. A check that only ever
saw `libx264` + mp4 is one the agent will trip over the first time it renders a
WebM. Every codec here is generated on demand and skipped if ffmpeg lacks the
encoder, so the suite stays green on a minimal ffmpeg.
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

from framegx import Video, inspect_video  # noqa: E402
from framegx.probe import probe  # noqa: E402
from gxcore import WARN  # noqa: E402

# (name, suffix, encoder args)
CODECS = [
    ("h264", ".mp4", ["-c:v", "libx264", "-pix_fmt", "yuv420p"]),
    ("mpeg4", ".mp4", ["-c:v", "mpeg4"]),
    ("vp9", ".webm", ["-c:v", "libvpx-vp9", "-b:v", "0"]),
    ("vp8", ".webm", ["-c:v", "libvpx"]),
    ("theora", ".ogv", ["-c:v", "libtheora"]),
    ("gif", ".gif", ["-c:v", "gif"]),
]

_MOTION = "testsrc=size=160x90:rate=10:duration=2"


def _encode(
    tmp_path: Path, name: str, suffix: str, args: list[str], *, audio: bool = False
) -> Path:
    out = tmp_path / f"{name}{suffix}"
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", _MOTION]
    if audio:
        cmd += ["-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-shortest"]
    cmd += [*args, str(out)]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0 or not out.exists():
        pytest.skip(f"{name} encoder unavailable: {result.stderr.decode(errors='replace')[:160]}")
    return out


@pytest.mark.parametrize(("name", "suffix", "args"), CODECS, ids=[c[0] for c in CODECS])
def test_each_codec_is_probed_and_inspected(tmp_path, name, suffix, args):
    path = _encode(tmp_path, name, suffix, args)
    meta = probe(path)
    assert meta["width"] == 160 and meta["height"] == 90
    report = inspect_video(Video(path=str(path), name=name))
    assert not any(p.code in ("probe-error", "no-frames") for p in report.problems)
    assert report.errors == 0


def test_audio_track_is_detected(tmp_path):
    path = _encode(
        tmp_path, "with_audio", ".mp4", ["-c:v", "libx264", "-pix_fmt", "yuv420p"], audio=True
    )
    assert probe(path)["has_audio"] is True
    report = inspect_video(Video(path=str(path), expect_audio=True))
    assert not any(p.code == "no-audio" for p in report.problems)


def test_silent_audio_is_reported(tmp_path):
    out = tmp_path / "silent.mp4"
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            _MOTION,
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo",
            "-shortest",
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
    report = inspect_video(Video(path=str(out), expect_audio=True))
    assert any(p.code == "silent-audio" and p.severity == WARN for p in report.problems)


def test_odd_dimensions_do_not_break_sampling(tmp_path):
    out = tmp_path / "odd.mp4"
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=161x91:rate=7:duration=2",
            "-c:v",
            "mpeg4",
            str(out),
        ],
        capture_output=True,
    )
    if result.returncode != 0:
        pytest.skip("mpeg4 unavailable")
    report = inspect_video(Video(path=str(out)))
    assert not any(p.code in ("probe-error", "no-frames") for p in report.problems)


def test_audio_only_file_is_a_probe_error(tmp_path):
    out = tmp_path / "tone.mp3"
    result = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=duration=1", str(out)],
        capture_output=True,
    )
    if result.returncode != 0:
        pytest.skip("mp3 encoder unavailable")
    report = inspect_video(Video(path=str(out)))
    assert any(p.code == "probe-error" for p in report.problems)
