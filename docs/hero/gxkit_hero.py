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
COLOURS = hero_domains.colours()


class GxkitHero(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(phi=62 * m.DEGREES, theta=-55 * m.DEGREES)

        title = m.Text("gxkit", font_size=64).to_corner(m.UL, buff=0.8)
        # 20, not 26: "sixteen domains" is longer than "ten", and at 26 the line
        # ran off the right edge of the frame. Measured, then looked at.
        sub = m.Text(hero_domains.subtitle(), font_size=20, color="#94a3b8")
        sub.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.12)
        self.add_fixed_in_frame_mobjects(title, sub)

        core = m.Cube(side_length=1.5, fill_opacity=0.95)
        core.set_fill("#e2e8f0")
        self.play(m.Create(core), run_time=1.0)

        cubes = m.VGroup()
        radius = 3.0
        for index, colour in enumerate(COLOURS):
            angle = math.pi / 2 + 2 * math.pi * index / len(COLOURS)
            cube = m.Cube(side_length=0.55, fill_opacity=0.95)
            cube.set_fill(colour)
            cube.move_to([radius * math.cos(angle), radius * math.sin(angle),
                          0.7 * math.sin(2 * angle)])
            cubes.add(cube)

        self.play(m.LaggedStart(*[m.Create(c) for c in cubes], lag_ratio=0.10),
                  run_time=2.6)
        self.begin_ambient_camera_rotation(rate=0.32)
        self.wait(1.5)

        # One domain's problem is found and fixed. The index is named, not guessed:
        # whatever sits there is the example the README tells the story about.
        fixed = DOMAINS.index("levelgx")
        self.play(cubes[fixed].animate.set_fill(hero_domains.FIXED), run_time=0.8)
        self.wait(3.5)
