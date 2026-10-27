"""Every tool must actually draw — not just analyse.

Most tests pass `--no-storyboard`, so the renderers (the images a human reviews)
would only be exercised by chance. These run each tool's CLI end to end, write a
PNG, and assert it is a real, non-blank picture. A storyboard is the point of the
family; a renderer that silently produced a blank canvas would defeat it.
"""

from __future__ import annotations

import importlib
import shutil
from pathlib import Path

import pytest
from gxcore.cli import run
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]

# (clean example, faulty example) per tool
EXAMPLES = {
    "chartgx": ("good_chart.py", "bad_chart.py"),
    "levelgx": ("good_level.py", "softlock_level.py"),
    "flowgx": ("good_machine.py", "broken_machine.py"),
    "protogx": ("good_protocol.py", "broken_protocol.py"),
    "authzgx": ("good_auth.py", "escalate_auth.py"),
    "depsgx": ("good_modules.py", "broken_modules.py"),
    "schemagx": ("good_schema.py", "broken_schema.py"),
    "docgx": ("good_page.py", "crowded_page.py"),
    "shadergx": ("good_shader.py", "broken_shader.py"),
    "framegx": ("good_clip.py", "frozen_clip.py"),
    "apigx": ("good_api.py", "broken_api.py"),
    "netgx": ("good_network.py", "broken_network.py"),
    "envgx": ("good_env.py", "broken_env.py"),
    "pipegx": ("good_pipeline.py", "broken_pipeline.py"),
    "seedgx": ("good_seed.py", "broken_seed.py"),
    "crongx": ("good_schedule.py", "broken_schedule.py"),
    "checkgx": ("good_registry.py", "broken_registry.py"),
}


def _require(name: str) -> None:
    if name == "shadergx":
        gl = pytest.importorskip("shadergx.gl")
        try:
            gl.context()
        except Exception:
            pytest.skip("no GL context")
    if name == "framegx" and not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        pytest.skip("no ffmpeg / ffprobe")


def _example(name: str, which: int) -> str:
    return str(ROOT / "packages" / name / "examples" / EXAMPLES[name][which])


def _tool(name: str):
    return importlib.import_module(f"{name}.tool").TOOL


def _assert_non_blank(path: Path) -> None:
    assert path.exists(), f"{path} was not written"
    img = Image.open(path).convert("RGB")
    assert img.width > 1 and img.height > 1
    colors = img.getcolors(maxcolors=1 << 20)
    assert colors is not None and len(colors) > 1, f"{path} is a blank canvas"


@pytest.mark.parametrize("name", list(EXAMPLES))
def test_storyboard_of_a_clean_artifact_is_written(tmp_path, name):
    _require(name)
    out = tmp_path / f"{name}.storyboard.png"
    assert run(_tool(name), ["inspect", _example(name, 0), "-o", str(out)]) == 0
    _assert_non_blank(out)


@pytest.mark.parametrize("name", list(EXAMPLES))
def test_render_subcommand_writes_a_png(tmp_path, name):
    _require(name)
    out = tmp_path / f"{name}.png"
    assert run(_tool(name), ["render", _example(name, 0), "-o", str(out)]) == 0
    _assert_non_blank(out)


def test_storyboard_annotates_a_faulty_artifact(tmp_path):
    out = tmp_path / "softlock.storyboard.png"
    assert run(_tool("levelgx"), ["inspect", _example("levelgx", 1), "-o", str(out)]) == 1
    _assert_non_blank(out)


@pytest.mark.parametrize("name", list(EXAMPLES))
@pytest.mark.parametrize("which", [0, 1])
def test_every_located_problem_is_the_number_the_picture_shows(name, which):
    """The documented promise: the text report and the picture agree.

    Every problem that carries a location is boxed, and the number on the box is
    that problem's number in the report — so "box 3" is not a claim about pixels
    but about the data the picture was drawn from.
    """
    from gxcore.storyboard import labelled_boxes

    _require(name)
    tool = _tool(name)
    scene = tool.load(Path(_example(name, which)))
    report = tool.inspect(scene)
    located = [
        (number, problem) for number, problem in enumerate(report.sorted(), 1) if problem.bbox
    ]
    drawn = labelled_boxes(report.problems, height=800)
    # Every located problem is numbered, in the report's own order, and the
    # number sits on a box drawn from that problem's location. Problems sharing a
    # location share one box, so the numbers on it are exactly theirs.
    drawn_numbers = [number for box in drawn for number in box.numbers]
    # Every located problem is numbered exactly once. Which box is drawn first is
    # a drawing detail; that each number exists, and lands on its own location, is
    # the promise the report and the picture share.
    assert sorted(drawn_numbers) == [n for n, _ in located], (
        f"{name}/{which}: the picture does not number every located problem once"
    )
    for box in drawn:
        x0, y0, x1, y1 = box.rectangle
        assert x1 > x0 and y1 > y0, f"{name}/{which}: a degenerate box {box.rectangle}"
        assert box.problem.bbox is not None
        where = tuple(round(value) for value in box.problem.bbox)
        sharing = [
            number
            for number, problem in located
            if problem.bbox and tuple(round(value) for value in problem.bbox) == where
        ]
        assert list(box.numbers) == sharing, (
            f"{name}/{which}: box at {where} carries {box.numbers}, expected {sharing}"
        )


def test_the_examples_cover_every_tool():
    from gxkit.registry import TOOLS

    assert set(EXAMPLES) == {tool.name for tool in TOOLS}
