# framegx

**Inspect a rendered animation.** ManimGX checks the *scene* before rendering;
`framegx` checks the *file that came out* — the part nothing else sees. A render
can look fine in the scene inspector and still be black, frozen, the wrong
length, or missing its sound.

One of the [`gxkit`](../../README.md) tools, built on [`gxcore`](../gxcore).
Needs `ffmpeg` / `ffprobe` on PATH.

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/framegx" framegx inspect clip.py
# local:  uvx --from ../../packages/framegx framegx inspect clip.py
```

## Pair it with a renderer (ManimGX)

```sh
manimgx render scene.py                 # ManimGX makes the video
framegx inspect clip.py                 # framegx checks the encoded result
```

Write the clip as a tiny file beside the video:

```python
import framegx as f

video = f.Video(
    "out.mp4",
    expected_duration=9.0,
    expected_fps=60,
    expected_size=(1920, 1080),
    expect_audio=True,
)
```

## The contract

```
$ framegx inspect frozen_clip.py
frozen_clip.py: A frozen render
video: demo_frozen.mp4
storyboard: A_frozen_render.storyboard.png
  file: demo_frozen.mp4
  160x90 at 10.00 fps, 2.00s, h264
  4 sampled moments at 2/s
inspect: 2 problems (1 error)
  [1] error frames 0-3  frozen: the picture is unchanged for 1.5s — the animation stopped
  [2] warn               single-color: every sampled frame is one flat colour — nothing varies
```

- **Exit code 1** on any `error`.
- `--json` for machines; `--no-storyboard` skips the contact sheet; `-o` names it.
- The storyboard is a **contact sheet** of sampled frames, with a frozen run boxed.

## Checks

| code | severity | what it means |
| --- | --- | --- |
| `missing-file` | error | the media file does not exist |
| `probe-error` | error | ffprobe/ffmpeg could not read it |
| `no-frames` | error | no frames could be decoded |
| `all-black` | error | every sampled frame is black |
| `frozen` | error | the picture is unchanged for `frozen_seconds` |
| `single-color` | warn | every frame is one flat colour |
| `no-motion` | warn | the first and last frames are identical |
| `duration-mismatch` | warn | the length differs from `expected_duration` |
| `wrong-fps` / `wrong-size` | warn | frame rate / size differs from what was declared |
| `no-audio` | warn | `expect_audio` is set but there is no audio track |
| `silent-audio` | warn | the audio track is silent (≤ −60 dBFS) |

## Why it can be trusted

Every check is proven to fire on a render with the fault and to stay quiet on one
without (`tests/`), using videos ffmpeg generates on the fly. The frame sampling
and metadata come from ffmpeg's own decode, not a re-implementation.

MIT licensed.
