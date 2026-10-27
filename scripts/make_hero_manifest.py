#!/usr/bin/env python3
"""Write `docs/assets/hero.json`: what the hero was rendered from, and the render.

A rendered asset is the easiest thing in a repository to leave behind, so the
manifest records the scene's *meaning* (not its bytes: reformatting or
re-commenting is not a new picture) and the GIF's bytes, plus the clip's measured
size, frame count and duration.

    python scripts/make_hero_manifest.py     # after rendering, before committing

Two earlier attempts were not portable, and CI caught both on the three Pythons
that are not this laptop's: `ast.dump` renders a tree differently across versions,
and the tokenizer splits an f-string on 3.12+ but not on 3.11. What is left is the
source text, with comments removed by a small state machine and whitespace
collapsed.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import runpy
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCENE = ROOT / "docs" / "hero" / "gxkit_hero.py"
DOMAINS = ROOT / "docs" / "hero" / "hero_domains.py"


def domain_count() -> int:
    """How many domains the scene draws — read from the module the scene reads.

    A written-down count is the defect this file exists to prevent: the hero said
    "ten domains" for six tools, and this manifest said sixteen after the
    seventeenth landed. The digests above are what refuse a stale render; this is
    the same number the picture was drawn from.
    """
    return len(runpy.run_path(str(DOMAINS))["domains"]())


GIF = ROOT / "docs" / "assets" / "hero.gif"
OUT = ROOT / "docs" / "assets" / "hero.json"

TRIPLE = ('"""', "'''")
QUOTES = ('"', "'")


def without_comments(source: str) -> str:
    """The source with comments removed, respecting string literals.

    A state machine rather than the tokenizer, because the tokenizer is not
    portable across the four Pythons this suite runs on (see the module docstring).
    A `#` inside a string survives, which is the whole point: a colour like
    `#22c55e` is code.
    """
    out: list[str] = []
    index = 0
    quote = ""
    while index < len(source):
        char = source[index]
        if not quote:
            if char == "#":
                while index < len(source) and source[index] != "\n":
                    index += 1
                continue
            three = source[index : index + 3]
            if three in TRIPLE:
                quote = three
                out.append(three)
                index += 3
                continue
            if char in QUOTES:
                quote = char
            out.append(char)
            index += 1
            continue
        if source.startswith(quote, index):
            out.append(quote)
            index += len(quote)
            quote = ""
            continue
        if char == "\\":
            out.append(source[index : index + 2])
            index += 2
            continue
        out.append(char)
        index += 1
    return "".join(out)


def source_digest(path: pathlib.Path) -> str:
    """A digest of the code, without its comments or its layout.

    Comments are dropped and runs of whitespace (line breaks, indentation, double
    spaces) are collapsed to one, so reformatting and re-commenting are not new
    pictures. What is left is the code as written on its lines — including the
    spaces around an operator, which is a deliberate limit: the tokenizer would
    normalise those, and the tokenizer is not portable (see the module docstring).
    """
    text = without_comments(path.read_text(encoding="utf-8"))
    return hashlib.sha256(re.sub(r"\s+", " ", text).strip().encode()).hexdigest()


def manifest() -> dict:
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,nb_frames,duration",
            "-of",
            "json",
            str(GIF),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    stream = json.loads(probe.stdout)["streams"][0]
    return {
        "scene": "docs/hero/gxkit_hero.py",
        "scene_sha256": source_digest(SCENE),
        "domains_source": "docs/hero/hero_domains.py",
        "domains_sha256": source_digest(DOMAINS),
        "hash_of": (
            "the scene's source with comments and layout removed, so reformatting or "
            "re-commenting does not demand a re-render while any change to what the "
            "code means does"
        ),
        "domains": domain_count(),
        "gif": "docs/assets/hero.gif",
        "gif_sha256": hashlib.sha256(GIF.read_bytes()).hexdigest(),
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "frames": int(stream["nb_frames"]),
        "duration_seconds": round(float(stream["duration"]), 2),
        "notes": (
            "Rendered with ManimGX at 720x720/24fps then converted (see the scene's "
            "docstring). The composition numbers in hero_domains.geometry() were "
            "measured against this render: 1.25 cube-diagonals of screen spacing, and "
            "the ring dropped so its top clears the 190 px title band."
        ),
    }


def main() -> int:
    OUT.write_text(json.dumps(manifest(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
