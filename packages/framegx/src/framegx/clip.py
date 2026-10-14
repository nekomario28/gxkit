"""A rendered animation, described by a small clip file.

    import framegx as f

    video = f.Video(
        "out.mp4",                 # path relative to this file
        expected_duration=9.0,
        expected_fps=60,
        expect_audio=True,
    )

ManimGX checks the *scene* before rendering; `framegx` checks the *rendered
file* — the part nothing else sees: is it black, frozen, the wrong length, or
missing its sound?
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

VIDEO_SUFFIXES = (".mp4", ".mov", ".mkv", ".webm", ".gif", ".avi")


@dataclass
class Video:
    path: str
    expected_duration: float | None = None
    expected_fps: float | None = None
    expected_size: tuple[int, int] | None = None
    expect_audio: bool = False
    frozen_seconds: float = 1.0
    sample_fps: float = 2.0
    name: str = "video"
    resolved_path: Path | None = None

    def resolved(self, base: str | Path) -> Path:
        p = Path(self.path)
        return p if p.is_absolute() else Path(base).parent / p


def _as_video(value: object) -> "Video | None":
    return value if isinstance(value, Video) else None


def load_video(path: str | Path) -> tuple[Video, object]:
    from gxcore.loading import load_module, resolve

    path = Path(path)
    module = load_module(path)
    video = resolve(
        module,
        attrs=("video", "VIDEO", "clip", "CLIP"),
        builders=("build", "make_video", "make"),
        convert=_as_video,
    )
    if video is None:
        media = getattr(module, "PATH", getattr(module, "path", None))
        if isinstance(media, str):
            video = Video(
                path=media,
                expected_duration=getattr(module, "EXPECTED_DURATION", None),
                expected_fps=getattr(module, "EXPECTED_FPS", None),
                expected_size=getattr(module, "EXPECTED_SIZE", None),
                expect_audio=bool(getattr(module, "EXPECT_AUDIO", False)),
                frozen_seconds=float(getattr(module, "FROZEN_SECONDS", 1.0)),
                sample_fps=float(getattr(module, "SAMPLE_FPS", 2.0)),
            )
    if video is None:
        raise ValueError(
            f"{path}: no video found — define `video` (a framegx.Video) or PATH=…"
        )
    if video.name == "video":
        video.name = getattr(module, "NAME", path.stem)
    video.resolved_path = video.resolved(path)
    return video, module


def clip(
    path: str,
    expected_duration: float | None = None,
    expected_fps: float | None = None,
    expected_size: tuple[int, int] | None = None,
    expect_audio: bool = False,
    frozen_seconds: float = 1.0,
    sample_fps: float = 2.0,
    name: str = "video",
) -> Video:
    return Video(path=path, expected_duration=expected_duration, expected_fps=expected_fps,
                 expected_size=expected_size, expect_audio=expect_audio,
                 frozen_seconds=frozen_seconds, sample_fps=sample_fps, name=name)
