"""framegx's domain knowledge: did the render actually come out right?

ManimGX checks the scene before rendering. This checks the rendered file — the
things a scene inspector cannot see: a black or frozen picture, the wrong length,
or missing sound.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from gxcore import ERROR, WARN, Problem, Report
from gxcore.geometry import union

from .clip import Video
from .probe import VideoError, mean_volume_db, probe, sample_frames
from .render import cell_box

_BLACK_LEVEL = 5.0  # 0..255 mean below this is "black"
_IDENTICAL = 0.5  # mean abs diff below this is "the same frame"
_MOTION = 0.5  # mean abs diff below this, first vs last, is "no motion"


def _compact(text: str, limit: int = 200) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return (lines[-1] if lines else "ffmpeg failed")[:limit]


def _longest_run(mask: np.ndarray[Any, Any]) -> tuple[int, int]:
    best_start = best_len = cur_start = cur_len = 0
    for i, flag in enumerate(mask):
        if flag:
            if cur_len == 0:
                cur_start = i
            cur_len += 1
            if cur_len > best_len:
                best_start, best_len = cur_start, cur_len
        else:
            cur_len = 0
    return best_start, best_len


def inspect_video(video: Video, name: str | None = None) -> Report:
    name = name or video.name
    media = video.resolved_path or Path(video.path)
    report = Report(name=name, subject=f"video: {media.name}", details=[f"file: {media.name}"])
    out: list[Problem] = []

    if not media.exists():
        out.append(Problem(ERROR, "missing-file", f"the media file does not exist: {media}"))
        report.problems = out
        return report

    try:
        meta = probe(media)
    except VideoError as exc:
        out.append(Problem(ERROR, "probe-error", _compact(str(exc))))
        report.problems = out
        return report

    fps = meta.get("fps")
    seconds = meta.get("duration")
    report.details.append(
        f"{meta['width']}x{meta['height']} at "
        f"{f'{fps:.2f}' if fps else '?'} fps, "
        f"{f'{seconds:.2f}' if seconds else '?'}s, {meta.get('codec')}"
    )

    if (
        video.expected_duration is not None
        and seconds is not None
        and abs(seconds - video.expected_duration) > 0.35
    ):
        out.append(
            Problem(
                WARN,
                "duration-mismatch",
                f"duration is {seconds:.2f}s, expected {video.expected_duration:.2f}s",
            )
        )
    if video.expected_fps is not None and fps is not None and abs(fps - video.expected_fps) > 0.5:
        out.append(
            Problem(WARN, "wrong-fps", f"frame rate is {fps:.2f}, expected {video.expected_fps:g}")
        )
    if video.expected_size is not None and (meta["width"], meta["height"]) != tuple(
        video.expected_size
    ):
        out.append(
            Problem(
                WARN,
                "wrong-size",
                f"size is {meta['width']}x{meta['height']}, "
                f"expected {video.expected_size[0]}x{video.expected_size[1]}",
            )
        )

    if video.expect_audio:
        if not meta["has_audio"]:
            out.append(Problem(WARN, "no-audio", "an audio track was expected, but there is none"))
        else:
            volume = mean_volume_db(media)
            if volume is not None and volume <= -60.0:
                out.append(
                    Problem(
                        WARN,
                        "silent-audio",
                        f"the audio track is silent (mean volume {volume:.1f} dBFS)",
                    )
                )

    try:
        frames = sample_frames(media, video.sample_fps)
    except VideoError as exc:
        out.append(Problem(ERROR, "probe-error", _compact(str(exc))))
        report.problems = out
        return report

    if frames.shape[0] == 0:
        out.append(Problem(ERROR, "no-frames", "no frames could be decoded"))
        report.problems = out
        return report

    n = frames.shape[0]
    report.details.append(f"{n} sampled moments at {video.sample_fps:g}/s")
    means = frames.reshape(n, -1).mean(axis=1)
    per_frame_ptp = frames.reshape(n, -1).max(axis=1) - frames.reshape(n, -1).min(axis=1)

    if float(np.max(means)) < _BLACK_LEVEL:
        out.append(Problem(ERROR, "all-black", "every sampled frame is black — nothing was drawn"))
    elif np.all(per_frame_ptp < _IDENTICAL):
        out.append(
            Problem(WARN, "single-color", "every sampled frame is one flat colour — nothing varies")
        )

    if n >= 3:
        diffs = np.abs(frames[1:].astype(np.int16) - frames[:-1].astype(np.int16))
        still = diffs.reshape(n - 1, -1).mean(axis=1) < _IDENTICAL
        start, length = _longest_run(still)
        if length / video.sample_fps >= video.frozen_seconds:
            run = range(start, start + length + 1)
            bbox = union([cell_box(i, n) for i in run])
            out.append(
                Problem(
                    ERROR,
                    "frozen",
                    f"the picture is unchanged for {length / video.sample_fps:.1f}s "
                    "(between two sampled moments) — the animation stopped",
                    label=f"frames {start}-{start + length}",
                    bbox=bbox,
                )
            )

    motion = float(np.abs(frames[-1].astype(int) - frames[0].astype(int)).mean())
    if (
        motion < _MOTION
        and float(np.max(per_frame_ptp)) > _IDENTICAL
        and float(np.max(means)) >= _BLACK_LEVEL
    ):
        out.append(
            Problem(
                WARN,
                "no-motion",
                "the first and last sampled frames are the same — the clip barely changes",
            )
        )

    if not out:
        report.details.append("the render looks healthy")

    report.problems = out
    return report
