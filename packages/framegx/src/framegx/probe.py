"""Read a rendered video with ffprobe/ffmpeg — the ground truth the checks use.

Everything here shells out to ffmpeg, so `framegx` needs ffmpeg on PATH and
nothing else; no decoding library, no OpenCV.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

SAMPLE_W, SAMPLE_H = 96, 54


class VideoError(Exception):
    """ffprobe or ffmpeg could not read the file."""


def _run(args: list[str], **kw: Any) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(args, capture_output=True, **kw)


def probe(path: str | Path) -> dict[str, Any]:
    """Metadata: size, fps, duration, whether there is audio."""
    result = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        text=True,
    )
    if result.returncode != 0:
        raise VideoError(result.stderr.strip() or f"ffprobe failed for {path}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise VideoError(f"ffprobe returned no JSON for {path}") from exc

    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise VideoError(f"{path} has no video stream")

    def as_float(value: str | None) -> float | None:
        if not value or value in ("0/0", "N/A"):
            return None
        if "/" in value:
            num, _, den = value.partition("/")
            try:
                return float(num) / float(den) if float(den) else None
            except ValueError:
                return None
        try:
            return float(value)
        except ValueError:
            return None

    duration = as_float(video.get("duration")) or as_float(data.get("format", {}).get("duration"))
    return {
        "width": int(video.get("width", 0)),
        "height": int(video.get("height", 0)),
        "fps": as_float(video.get("r_frame_rate")),
        "duration": duration,
        "has_audio": any(s.get("codec_type") == "audio" for s in streams),
        "codec": video.get("codec_name"),
    }


def sample_frames(path: str | Path, sample_fps: float = 2.0) -> np.ndarray[Any, Any]:
    """A small grayscale frame per sampled moment, as ``(N, SAMPLE_H, SAMPLE_W)``."""
    result = _run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-vf",
            f"fps={sample_fps},scale={SAMPLE_W}:{SAMPLE_H},format=gray",
            "-f",
            "rawvideo",
            "-",
        ]
    )
    if result.returncode != 0:
        raise VideoError(result.stderr.decode(errors="replace").strip() or "ffmpeg failed")
    frame_bytes = SAMPLE_W * SAMPLE_H
    count = len(result.stdout) // frame_bytes
    if count == 0:
        return np.zeros((0, SAMPLE_H, SAMPLE_W), dtype=np.uint8)
    return np.frombuffer(result.stdout[: count * frame_bytes], dtype=np.uint8).reshape(
        count, SAMPLE_H, SAMPLE_W
    )


def mean_volume_db(path: str | Path) -> float | None:
    """Integrated mean volume in dBFS, or None if there is no audio."""
    result = _run(
        ["ffmpeg", "-v", "info", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        text=True,
    )
    text = result.stderr
    for line in text.splitlines():
        if "mean_volume:" in line:
            try:
                return float(line.split("mean_volume:")[1].strip().split()[0])
            except (IndexError, ValueError):
                return None
    return None
