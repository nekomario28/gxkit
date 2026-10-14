---
name: framegx
description: Inspect a rendered animation file before showing it — the output a scene-level inspector cannot see. Catches a black frame, a frozen picture (the same frame for a second or more), a single flat colour, no motion, a wrong duration/frame-rate/size, and a missing or silent audio track. Use right after rendering a video with ManimGX (or ffmpeg, Blender, or anything) when you cannot watch the file yourself, especially in a CI or headless run. Needs ffmpeg. Not for scene layout / text overlap (that is manimgx inspect) and not for editing the video.
---

# framegx — check the render, not the scene

ManimGX's `inspect` checks the **scene** before rendering. `framegx` checks the
**file that came out** — the failures that appear only after encoding: black,
frozen, wrong length, silent. It pairs directly with a renderer.

## Install

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/framegx" framegx --help
uv tool install ./packages/framegx
```

Needs `ffmpeg` and `ffprobe`.

## The loop

```sh
manimgx render scene.py     # render the animation
framegx inspect clip.py     # check the encoded result
```

Clip file beside the video:

```python
import framegx as f

video = f.Video("out.mp4", expected_duration=9.0, expect_audio=True)
```

1. `framegx inspect clip.py` — metadata, problems with a stable `code`, and a
   **contact sheet** of sampled frames. **Exit 1 on any error.**
2. Look at the contact sheet; if every cell is the same, it is frozen.
3. Fix the scene and render again.

## What it catches

| code | severity | meaning |
| --- | --- | --- |
| `missing-file` | error | the media file is not there |
| `probe-error` | error | ffmpeg could not read it |
| `no-frames` | error | nothing decodable |
| `all-black` | error | every frame is black |
| `frozen` | error | the picture is unchanged ≥ `frozen_seconds` |
| `single-color` | warn | one flat colour throughout |
| `no-motion` | warn | first and last frames are identical |
| `duration-mismatch` | warn | not the length it declared |
| `wrong-fps` / `wrong-size` | warn | not the rate / size it declared |
| `no-audio` / `silent-audio` | warn | expected sound that is missing or silent |

`frozen` is the point: the scene played, the render "succeeded", but the file
shows one frame for a second or more. Every check has a test that proves it
fires on a render with the fault and stays quiet on one without (`tests/`).
