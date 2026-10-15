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
from gxcore.loading import loading_session
from gxcore.toolkit import distribution_version

from .codes import CODEBOOK
from .registry import BY_NAME, TOOLS, ToolSpec, detect


def _tools_table(as_json: bool) -> int:
    if as_json:
        print(
            json.dumps(
                [{"name": t.name, "inspects": t.inspects, "reads": list(t.reads)} for t in TOOLS],
                indent=2,
            )
        )
    else:
        width = max(len(t.name) for t in TOOLS)
        for t in TOOLS:
            print(f"{t.name:<{width}}  {t.inspects}")
    return 0


def _tool_for(path: Path, explicit: str | None) -> ToolSpec | None:
    if explicit:
        spec = BY_NAME.get(explicit)
        if spec is None:
            print(f"gxkit: unknown tool {explicit!r}; try `gxkit tools`", file=sys.stderr)
            return None
        return spec
    suffix = path.suffix.lower()
    if suffix != ".py":
        # Detection reads a Python module, so a foreign document (an OpenAPI spec,
        # say) cannot be recognised automatically. The registry declares which
        # suffixes each tool reads, so name the tool rather than making the reader
        # guess — and keep refusing to execute a non-Python file as Python.
        readers = [spec.name for spec in TOOLS if suffix in spec.reads]
        if len(readers) == 1:
            print(
                f"gxkit: {path.name} is not a Python artifact.\n"
                f"  The tool that reads {suffix} is {readers[0]}: "
                f"gxkit inspect {readers[0]} {path}",
                file=sys.stderr,
            )
        elif readers:
            # Several tools read this suffix and they read it differently (a
            # `.json` is an OpenAPI document to one and a chart declaration to
            # another), so which one is meant is the caller's decision.
            print(
                f"gxkit: {path.name} is not a Python artifact.\n"
                f"  {suffix} is read by {', '.join(readers)}; name the one you mean: "
                f"gxkit inspect <tool> {path}",
                file=sys.stderr,
            )
        else:
            print(
                f"gxkit: {path.name} is not a Python artifact, and no tool reads "
                f"{suffix or 'files with no suffix'}.\n"
                f"  `gxkit tools` lists what each tool inspects.",
                file=sys.stderr,
            )
        return None
    from gxcore.loading import load_module

    try:
        module = load_module(path)
        spec = detect(module)
    except (Exception, SystemExit) as exc:  # an artifact exit is not inspection success
        print(f"gxkit: {type(exc).__name__}: {exc}", file=sys.stderr)
        return None
    if spec is None:
        names = ", ".join(t.name for t in TOOLS)
        print(
            f"gxkit: could not tell which tool fits {path.name}.\n"
            f"  name one explicitly: gxkit inspect <tool> {path}\n"
            f"  tools: {names}",
            file=sys.stderr,
        )
    return spec


def _cmd_tools(args: argparse.Namespace) -> int:
    return _tools_table(args.json)


def _codes_table(as_json: bool, tool: str | None) -> int:
    if tool:
        if tool not in CODEBOOK:
            print(f"gxkit: unknown tool {tool!r}; try `gxkit tools`", file=sys.stderr)
            return 2
        book = {tool: CODEBOOK[tool]}
    else:
        book = CODEBOOK
    if as_json:
        print(json.dumps(book, indent=2))
        return 0
    for name, codes in book.items():
        print(f"{name}:")
        width = max((len(c) for c in codes), default=0)
        for code, severity in sorted(codes.items()):
            print(f"  {code:<{width}}  {severity}")
    return 0


def _cmd_codes(args: argparse.Namespace) -> int:
    return _codes_table(args.json, args.tool)


def _run_tool(spec: ToolSpec, file: Path, args: argparse.Namespace) -> int:
    tool = importlib.import_module(spec.module).TOOL
    forwarded = ["inspect", str(file)]
    if args.output:
        forwarded += ["-o", args.output]
    if args.json:
        forwarded.append("--json")
    if args.no_storyboard:
        forwarded.append("--no-storyboard")
    if args.no_config:
        forwarded.append("--no-config")
    if args.baseline:
        forwarded += ["--baseline", args.baseline]
    if args.write_baseline:
        forwarded += ["--write-baseline", args.write_baseline]
    print(f"gxkit: {spec.name} — {spec.inspects}", file=sys.stderr)
    return run(tool, forwarded)


def _cmd_inspect(args: argparse.Namespace) -> int:
    positional = list(args.path)
    explicit = None
    if positional and positional[0] in BY_NAME:
        explicit, positional = positional[0], positional[1:]
    elif (
        len(positional) >= 2
        and not Path(positional[0]).exists()
        and not positional[0].endswith(".py")
    ):
        # looks like a mistyped tool name beside a real path
        print(f"gxkit: unknown tool {positional[0]!r}; try `gxkit tools`", file=sys.stderr)
        return 2
    if not positional:
        print("gxkit: inspect needs a file or a directory", file=sys.stderr)
        return 2

    files: list[Path] = []
    for raw in positional:
        # Resolve every input before any artifact executes: an artifact may
        # change the process directory, and a relative path would then name a
        # different file for routing, loading and reporting alike.
        target = Path(raw).resolve()
        if target.is_dir():
            found = sorted(target.rglob("*.py"))
            if not found:
                print(f"gxkit: no *.py artifacts under {target}", file=sys.stderr)
                return 2
            files += found
        else:
            files.append(target)

    if len(files) > 1 and (args.json or args.output or args.baseline or args.write_baseline):
        print("gxkit: --json, -o and a baseline take a single artifact", file=sys.stderr)
        return 2

    rc = 0
    for file in files:
        with loading_session():
            spec = _tool_for(file, explicit)
            if spec is None:
                rc = max(rc, 2)
                continue
            rc = max(rc, _run_tool(spec, file, args))
    return rc


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gxkit",
        description="Route an artifact to the gxkit tool that inspects it.",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"gxkit {distribution_version('gxkit-cli')}",
    )
    sub = p.add_subparsers(dest="command", required=True)

    tools = sub.add_parser("tools", help="list the tools and what they inspect")
    tools.add_argument("--json", action="store_true")
    tools.set_defaults(func=_cmd_tools)

    codes = sub.add_parser("codes", help="list every problem code and its severity")
    codes.add_argument("tool", nargs="?", help="one tool, or all")
    codes.add_argument("--json", action="store_true")
    codes.set_defaults(func=_cmd_codes)

    ins = sub.add_parser("inspect", help="detect the artifact's tool and inspect it")
    ins.add_argument("path", nargs="+", help="[<tool>] <file.py|directory>")
    ins.add_argument("-o", "--output", help="storyboard path")
    ins.add_argument("--json", action="store_true")
    ins.add_argument("--no-storyboard", action="store_true")
    ins.add_argument("--no-config", action="store_true", help="ignore .gxkit.toml")
    ins.add_argument("--baseline", help="compare against a stored baseline report")
    ins.add_argument("--write-baseline", help="write this report as the baseline")
    ins.set_defaults(func=_cmd_inspect)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"gxkit: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
