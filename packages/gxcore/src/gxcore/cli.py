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
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .baseline import Baseline, Diff, compare, summary
from .config import apply as apply_config
from .config import load as load_config
from .model import Report
from .report import human, to_json
from .storyboard import annotate, storyboard_path

Load = Callable[[Path], Any]
Inspect = Callable[[Any], Report]
Render = Callable[[Any, Path | None, float | None], Path]
ToImage = Callable[[Any], Any]


def printable_output() -> None:
    """Let a report print on a console that cannot encode every character.

    Messages name what they found, and some of those names are not in every
    console's code page (an arrow in an edge, a degree sign). Losing the report
    to an encoding error would turn a real verdict into an input failure, so
    unencodable characters are escaped instead.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="backslashreplace")


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
    ins.add_argument("--no-config", action="store_true", help="ignore .gxkit.toml")
    ins.add_argument("--baseline", help="compare against a stored baseline report")
    ins.add_argument("--write-baseline", help="write this report as the baseline")

    ren = sub.add_parser("render", help="write the artifact as a PNG")
    ren.add_argument("file", help="the file that builds the artifact")
    ren.add_argument("-o", "--output", help="PNG path")
    ren.add_argument("--dpi", type=float, default=None, help="output DPI")
    return p


def _cmd_inspect(
    tool: Tool, args: argparse.Namespace, known_tools: Iterable[str] | None = None
) -> int:
    # The artifact may change the process directory while it loads, so its
    # identity is fixed before it executes; the report still names the file.
    path = Path(args.file).resolve()
    artifact = tool.load(path)
    report = tool.inspect(artifact)
    if not getattr(args, "no_config", False):
        apply_config(report, load_config(path.parent, known_tools), tool.name)

    diff: Diff | None = None
    if args.baseline:
        diff = compare(report, Baseline.load(args.baseline))
    if args.write_baseline:
        Baseline.of(report).save(args.write_baseline)
        print(f"{tool.name}: baseline written to {args.write_baseline}", file=sys.stderr)

    sb: Path | None = None
    if not args.no_storyboard and tool.to_image is not None:
        # A storyboard the tool cannot draw (e.g. shadergx with no GL context)
        # must not swallow the report that was already computed.
        try:
            sb = storyboard_path(report.name, args.output)
            annotate(tool.to_image(artifact), report.problems, sb, origin=tool.origin)
        except Exception as exc:
            if args.output:
                # An explicit `-o` that produces no file is a request this cannot
                # honour: measured, a declared chart exits 0 with no image and only a
                # line on stderr, which reads as success until someone looks for the
                # file. A refusal names the reason instead.
                print(
                    f"{tool.name}: cannot write {args.output}: {type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )
                return 2
            print(f"{tool.name}: storyboard skipped ({type(exc).__name__}: {exc})", file=sys.stderr)
            sb = None

    if args.json:
        print(to_json(report, sb, diff))
    else:
        text = human(path, report, sb)
        if diff is not None:
            text = f"{text}\n{summary(diff)}"
        print(text)
    # With a baseline, only *new* errors fail — pre-existing debt does not.
    failing = diff.new_errors if diff is not None else report.errors
    return 1 if failing else 0


def _cmd_render(tool: Tool, args: argparse.Namespace) -> int:
    path = Path(args.file).resolve()
    artifact = tool.load(path)
    out = Path(args.output) if args.output else Path(f"{path.stem}.png")
    print(tool.render(artifact, out, args.dpi))
    return 0


def run(tool: Tool, argv: list[str] | None = None, known_tools: Iterable[str] | None = None) -> int:
    printable_output()
    args = _build_parser(tool).parse_args(argv)
    try:
        if args.command == "inspect":
            return _cmd_inspect(tool, args, known_tools)
        return _cmd_render(tool, args)
    except FileNotFoundError as e:
        print(f"{tool.name}: no such file: {e}", file=sys.stderr)
        return 2
    except SystemExit as e:
        print(
            f"{tool.name}: the artifact called sys.exit({e.code!r}) while loading", file=sys.stderr
        )
        return 2
    except Exception as e:  # a broken artifact file must report, not traceback
        print(f"{tool.name}: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
