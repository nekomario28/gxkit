"""A render that failed: the picture never changes, so the animation is dead.

The common failure this catches that a scene-level inspector cannot: the scene
looked fine, but the file that came out is frozen (or black).
"""

import framegx as f

NAME = "A frozen render"

video = f.Video("demo_frozen.mp4", expected_duration=2.0)
