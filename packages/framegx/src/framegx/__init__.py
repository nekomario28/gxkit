"""framegx — inspect a rendered animation (the output a scene inspector cannot see).

Write the clip as a tiny Python file — `video = framegx.Video("out.mp4", …)` —
then `framegx inspect clip.py` decodes it with ffmpeg and reports whether the
render is black, frozen, the wrong length, or missing its sound, with a contact
sheet as the storyboard.
"""

from gxcore import ERROR, INFO, WARN, Problem, Report

from .checks import inspect_video
from .clip import Video, clip, load_video
from .probe import VideoError, mean_volume_db, probe, sample_frames
from .render import contact_sheet
from .tool import TOOL, Scene, main

__all__ = [
    "ERROR",
    "INFO",
    "TOOL",
    "WARN",
    "Problem",
    "Report",
    "Scene",
    "Video",
    "VideoError",
    "clip",
    "contact_sheet",
    "inspect_video",
    "load_video",
    "main",
    "mean_volume_db",
    "probe",
    "sample_frames",
]
__version__ = "0.1.0"
