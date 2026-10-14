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
