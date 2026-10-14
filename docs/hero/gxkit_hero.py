import math

import manimgx as m

m.config.background_color = "#0b1020"

PALETTE = ["#2563eb", "#0d9488", "#16a34a", "#ca8a04", "#f59e0b",
           "#ea580c", "#dc2626", "#9f1239", "#7c3aed", "#db2777"]


class GxkitHero(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(phi=62 * m.DEGREES, theta=-55 * m.DEGREES)

        title = m.Text("gxkit", font_size=64).to_corner(m.UL, buff=0.8)
        sub = m.Text("one core \u00b7 ten domains \u00b7 inspect, then ship",
                     font_size=26, color="#94a3b8")
        sub.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.12)
        self.add_fixed_in_frame_mobjects(title, sub)

        core = m.Cube(side_length=1.5, fill_opacity=0.95)
        core.set_fill("#e2e8f0")
        self.play(m.Create(core), run_time=1.0)

        cubes = m.VGroup()
        radius = 3.3
        for i, colour in enumerate(PALETTE):
            a = math.pi / 2 + 2 * math.pi * i / len(PALETTE)
            cube = m.Cube(side_length=0.7, fill_opacity=0.95)
            cube.set_fill(colour)
            cube.move_to([radius * math.cos(a), radius * math.sin(a),
                          0.9 * math.sin(2 * a)])
            cubes.add(cube)

        self.play(m.LaggedStart(*[m.Create(c) for c in cubes], lag_ratio=0.12),
                  run_time=2.6)
        self.begin_ambient_camera_rotation(rate=0.32)
        self.wait(1.5)

        # one domain's problem is found and fixed
        self.play(cubes[6].animate.set_fill("#16a34a"), run_time=0.8)
        self.wait(3.5)
