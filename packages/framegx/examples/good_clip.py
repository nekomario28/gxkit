"""A render that should pass: it moves, and it is the length and size it claims."""

import framegx as f

NAME = "A moving render"

video = f.Video(
    "demo_motion.mp4",
    expected_duration=2.0,
    expected_fps=10,
    expected_size=(160, 90),
)
