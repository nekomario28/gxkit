# framegx, for AI agents

A person pointed you here. You just rendered an animation (with ManimGX or
anything else) but you cannot watch the file. `framegx` reads it and tells you
whether it actually came out: black, frozen, the wrong length, or silent.

Part of `gxkit`; the review contract (`inspect`, `--json`, exit codes,
storyboard) is shared with every other tool in the family. Needs `ffmpeg`.

## Set it up

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/framegx" framegx --help
uv tool install ./packages/framegx
```

## Write a clip

Beside the video, a tiny file:

```python
import framegx as f

video = f.Video(
    "out.mp4",                 # relative to this clip file
    expected_duration=9.0,
    expect_audio=True,
)
```

Or module-level `PATH` / `EXPECTED_DURATION` / `EXPECTED_FPS` / `EXPECTED_SIZE` /
`EXPECT_AUDIO`.

## The loop

1. **Render** the animation (`manimgx render scene.py` → `out.mp4`).
2. **Inspect** — `framegx inspect clip.py`. It prints the metadata, every
   problem with a stable `code`, and writes `<name>.storyboard.png` (a contact
   sheet). **Exit 1 means at least one error.**
3. **Look** at the contact sheet: a black or identical grid is the bug.
4. Fix the scene and render again.

## Reading the report

- `error` — the render is broken: `all-black`, `frozen`, `no-frames`,
  `probe-error`, `missing-file`. Exit code 1.
- `warn` — `single-color`, `no-motion`, `duration-mismatch`, `wrong-fps`,
  `wrong-size`, `no-audio`, `silent-audio`.

`frozen` is the one a scene-level inspector misses: the scene played, but the
file shows the same frame for a second or more.
