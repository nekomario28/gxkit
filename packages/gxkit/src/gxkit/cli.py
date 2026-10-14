"""`gxkit` — one entry point for the whole family.

    gxkit tools                  # what can be inspected
    gxkit inspect chart.py       # detect the artifact and route to its tool
    gxkit inspect levelgx x.py   # or name the tool explicitly

Detection reads the file's own object (a `Machine`, a `Level`, a `Schema`, …)
so an agent does not have to know which tool fits — the promise the family skill
makes, made executable.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

from gxcore.cli import run

from .registry import BY_NAME, TOOLS, detect


def _tools_table(as_json: bool) -> int:
    if as_json:
        print(json.dumps([{"name": t.name, "inspects": t.inspects} for t in TOOLS], indent=2))
    else:
        width = max(len(t.name) for t in TOOLS)
        for t in TOOLS:
            print(f"{t.name:<{width}}  {t.inspects}")
    return 0


def _tool_for(path: Path, explicit: str | None):
    if explicit:
        spec = BY_NAME.get(explicit)
        if spec is None:
            print(f"gxkit: unknown tool {explicit!r}; try `gxkit tools`", file=sys.stderr)
            return None
        return spec
    from gxcore.loading import load_module

    try:
        module = load_module(path)
    except Exception as exc:  # a broken artifact reports, does not traceback
        print(f"gxkit: {type(exc).__name__}: {exc}", file=sys.stderr)
        return None
    spec = detect(module)
    if spec is None:
        names = ", ".join(t.name for t in TOOLS)
        print(f"gxkit: could not tell which tool fits {path.name}.\n"
              f"  name one explicitly: gxkit inspect <tool> {path}\n"
              f"  tools: {names}", file=sys.stderr)
    return spec


def _cmd_tools(args: argparse.Namespace) -> int:
    return _tools_table(args.json)


def _cmd_inspect(args: argparse.Namespace) -> int:
    positional = list(args.path)
    explicit = None
    # "<tool> <file>" when the first name is a known tool, or when a second
    # positional is clearly the file (a .py path) — so an unknown tool name
    # reports "unknown tool" instead of being mistaken for the file.
    if len(positional) >= 2 and (positional[0] in BY_NAME or positional[1].endswith(".py")
                                 or Path(positional[1]).exists()):
        explicit, positional = positional[0], positional[1:]
    path = Path(positional[0])
    spec = _tool_for(path, explicit)
    if spec is None:
        return 2

    tool = importlib.import_module(spec.module).TOOL
    forwarded = ["inspect", str(path)]
    if args.output:
        forwarded += ["-o", args.output]
    if args.json:
        forwarded.append("--json")
    if args.no_storyboard:
        forwarded.append("--no-storyboard")
    print(f"gxkit: {spec.name} — {spec.inspects}", file=sys.stderr)
    return run(tool, forwarded)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gxkit", description=__doc__.splitlines()[0])
    p.add_argument("--version", action="version", version="gxkit 0.1.0")
    sub = p.add_subparsers(dest="command", required=True)

    tools = sub.add_parser("tools", help="list the tools and what they inspect")
    tools.add_argument("--json", action="store_true")
    tools.set_defaults(func=_cmd_tools)

    ins = sub.add_parser("inspect", help="detect the artifact's tool and inspect it")
    ins.add_argument("path", nargs="+", help="[<tool>] <file.py>")
    ins.add_argument("-o", "--output", help="storyboard path")
    ins.add_argument("--json", action="store_true")
    ins.add_argument("--no-storyboard", action="store_true")
    ins.set_defaults(func=_cmd_inspect)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"gxkit: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
