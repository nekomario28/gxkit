"""The CLI every `*gx` tool gets for free.

A tool supplies four callables and gets the whole agent contract:

    Tool(
        name="chartgx",
        description="...",
        load=...,        # Path -> artifact
        inspect=...,     # artifact -> Report
        render=...,      # (artifact, Path|None, dpi|None) -> Path
        to_image=...,    # artifact -> PIL.Image (for the storyboard), or None
    )

`gxcore.cli.run(tool)` then offers ``inspect`` and ``render`` with ``--json``,
``--no-storyboard``, ``-o`` and the exit-code policy.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from .model import Report
from .report import human, to_json
from .storyboard import annotate, storyboard_path

Load = Callable[[Path], Any]
Inspect = Callable[[Any], Report]
Render = Callable[[Any, Optional[Path], Optional[float]], Path]
ToImage = Callable[[Any], Any]


@dataclass
class Tool:
    name: str
    description: str
    load: Load
    inspect: Inspect
    render: Render
    to_image: ToImage | None = None
    version: str = "0.0.0"
    origin: str = "bottom-left"


def _build_parser(tool: Tool) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog=tool.name, description=tool.description)
    p.add_argument("--version", action="version", version=f"{tool.name} {tool.version}")
    sub = p.add_subparsers(dest="command", required=True)

    ins = sub.add_parser("inspect", help="report problems and write a storyboard")
    ins.add_argument("file", help="the file that builds the artifact")
    ins.add_argument("-o", "--output", help="storyboard path")
    ins.add_argument("--no-storyboard", action="store_true", help="skip the storyboard image")
    ins.add_argument("--json", action="store_true", help="print the report as JSON")

    ren = sub.add_parser("render", help="write the artifact as a PNG")
    ren.add_argument("file", help="the file that builds the artifact")
    ren.add_argument("-o", "--output", help="PNG path")
    ren.add_argument("--dpi", type=float, default=None, help="output DPI")
    return p


def _cmd_inspect(tool: Tool, args: argparse.Namespace) -> int:
    artifact = tool.load(Path(args.file))
    report = tool.inspect(artifact)

    sb: Path | None = None
    if not args.no_storyboard and tool.to_image is not None:
        # A storyboard the tool cannot draw (e.g. shadergx with no GL context)
        # must not swallow the report that was already computed.
        try:
            sb = storyboard_path(report.name, args.output)
            annotate(tool.to_image(artifact), report.problems, sb, origin=tool.origin)
        except Exception as exc:
            print(f"{tool.name}: storyboard skipped ({type(exc).__name__}: {exc})", file=sys.stderr)
            sb = None

    if args.json:
        print(to_json(report, sb))
    else:
        print(human(args.file, report, sb))
    return 1 if report.errors else 0


def _cmd_render(tool: Tool, args: argparse.Namespace) -> int:
    artifact = tool.load(Path(args.file))
    out = Path(args.output) if args.output else Path(f"{Path(args.file).stem}.png")
    print(tool.render(artifact, out, args.dpi))
    return 0


def run(tool: Tool, argv: list[str] | None = None) -> int:
    args = _build_parser(tool).parse_args(argv)
    try:
        if args.command == "inspect":
            return _cmd_inspect(tool, args)
        return _cmd_render(tool, args)
    except FileNotFoundError as e:
        print(f"{tool.name}: no such file: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # a broken artifact file must report, not traceback
        print(f"{tool.name}: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
