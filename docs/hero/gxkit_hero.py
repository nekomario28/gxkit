"""The README's hero: one core, one cube per domain, and one of them fixed.

The domains come from `hero_domains`, which reads `packages/` — so a new tool
changes the picture instead of contradicting it. Render with:

    uvx --python 3.14 manimgx render docs/hero/gxkit_hero.py -r 720x720 --fps 24
    ffmpeg -i media/videos/gxkit_hero/720p24/GxkitHero.mp4 -vf "fps=12,scale=560:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse" -loop 0 docs/assets/hero.gif

then update `docs/assets/hero.json` (the test refuses a scene that was edited
without being drawn again), and look at the frames before committing.
"""

import math

import manimgx as m

import hero_domains

m.config.background_color = "#0b1020"

DOMAINS = hero_domains.domains()

#: The elevation the ring's projection was measured at (see `hero_domains.SQUASH`):
#: the ring's minor axis is 0.81 of its major one here, against 0.49 at 62°, which
#: is what made sixteen cubes look like they overlapped when they did not touch.
ELEVATION_DEGREES = 40


class GxkitHero(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(phi=ELEVATION_DEGREES * m.DEGREES, theta=-55 * m.DEGREES)
        radius, side, depth, drop = hero_domains.geometry(len(DOMAINS))

        title = m.Text("gxkit", font_size=64).to_corner(m.UL, buff=0.8)
        sub = m.Text(hero_domains.subtitle(), font_size=20, color="#94a3b8")
        sub.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.12)
        self.add_fixed_in_frame_mobjects(title, sub)

        core = m.Cube(side_length=1.5, fill_opacity=0.95)
        core.set_fill("#e2e8f0")
        self.play(m.Create(core), run_time=1.0)

        # The wave runs along the view axis, so depth cannot close the gap the
        # spacing was derived to keep open.
        phi = math.radians(ELEVATION_DEGREES)
        theta = math.radians(-55)
        view = (
            math.cos(phi) * math.cos(theta),
            math.cos(phi) * math.sin(theta),
            math.sin(phi),
        )

        # The screen's vertical, so `drop` moves the ring down the picture rather
        # than along a scene axis that the camera happens to tilt.
        up = (-math.sin(phi) * math.cos(theta), -math.sin(phi) * math.sin(theta), math.cos(phi))

        cubes = m.VGroup()
        for index, colour in enumerate(hero_domains.colours()):
            angle = math.pi / 2 + 2 * math.pi * index / len(DOMAINS)
            cube = m.Cube(side_length=side, fill_opacity=0.95)
            cube.set_fill(colour)
            offset = depth * math.sin(2 * angle)
            cube.move_to(
                [
                    radius * math.cos(angle) + offset * view[0] + drop * up[0],
                    radius * math.sin(angle) + offset * view[1] + drop * up[1],
                    offset * view[2] + drop * up[2],
                ]
            )
            cubes.add(cube)

        self.play(m.LaggedStart(*[m.Create(c) for c in cubes], lag_ratio=0.10), run_time=2.6)
        self.begin_ambient_camera_rotation(rate=0.32)
        self.wait(1.5)

        # One domain's problem is found and fixed. The index is named, not guessed:
        # whatever sits there is the example the README tells the story about.
        fixed = DOMAINS.index("levelgx")
        self.play(cubes[fixed].animate.set_fill(hero_domains.FIXED), run_time=0.8)
        self.wait(3.5)
