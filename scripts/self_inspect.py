"""Inspect the family's own module graph with the family.

The layering this repository claims — a shared core, thin domain tools, one
umbrella that routes to them — is an invariant nothing else checks. Deriving the
real graph from the sources and inspecting it with `gxkit` both proves the
invariant and dogfoods the inspector on an artifact of realistic size.

The umbrella imports its tools dynamically, so its edges come from its own
routing table rather than from a static import scan. Nothing here is
hand-written; the graph is the repository's.
"""

from __future__ import annotations

import ast
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


def internal_packages() -> set[str]:
    sys.path.insert(0, str(ROOT / "packages/gxkit/src"))
    try:
        from gxkit.registry import TOOLS

        return {"gxcore", "gxkit", *(spec.name for spec in TOOLS)}
    finally:
        sys.path.pop(0)


def import_edges(internal: set[str]) -> list[tuple[str, str]]:
    """Every package-to-package import the sources actually contain."""
    edges: set[tuple[str, str]] = set()
    for pyproject in sorted((ROOT / "packages").glob("*/pyproject.toml")):
        package = pyproject.parent.name
        for path in sorted((pyproject.parent / "src").rglob("*.py")):
            for node in ast.walk(ast.parse(path.read_bytes(), filename=str(path))):
                if isinstance(node, ast.Import):
                    names = [alias.name.split(".")[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module.split(".")[0]]
                else:
                    continue
                for name in names:
                    if name in internal and name != package:
                        edges.add((package, name))
    return sorted(edges)


def routed_edges(internal: set[str]) -> list[tuple[str, str]]:
    """The umbrella's edges, from the table it routes by."""
    sys.path.insert(0, str(ROOT / "packages/gxkit/src"))
    try:
        from gxkit.registry import TOOLS

        return sorted(
            {("gxkit", spec.module.split(".")[0]) for spec in TOOLS} - {("gxkit", "gxkit")}
        )
    finally:
        sys.path.pop(0)


def build_artifact(modules: list[str], edges: list[tuple[str, str]], domains: list[str]) -> str:
    return (
        "import depsgx as d\n\n"
        "graph = d.ModuleGraph(\n"
        f"    modules={modules!r},\n"
        f"    depends={edges!r},\n"
        "    roots=['gxkit'],\n"
        f"    layers={[['gxkit'], domains, ['gxcore']]!r},\n"
        "    name='gxkit family',\n"
        ")\n"
    )


def family_graph() -> tuple[list[str], list[tuple[str, str]], list[str]]:
    """(modules, edges, domains) as the sources and the routing table declare them."""
    internal = internal_packages()
    edges = sorted({*import_edges(internal), *routed_edges(internal)})
    domains = sorted(internal - {"gxcore", "gxkit"})
    return sorted(internal), edges, domains


def check_layering(modules: list[str], edges: list[tuple[str, str]]) -> list[str]:
    """What the layering claim forbids, which a shared layer cannot express.

    Two tools in one layer may legitimately share it, so `depsgx` will not call a
    sibling dependency a violation. That this family forbids them is a claim of
    its own, and it belongs here rather than in the artifact.
    """
    domains = {name for name in modules if name not in {"gxcore", "gxkit"}}
    breaks = []
    for src, dst in edges:
        if src == "gxcore":
            breaks.append(f"the shared core must not depend on {dst!r}")
        elif src in domains and dst in domains:
            breaks.append(f"{src!r} must not depend on the sibling tool {dst!r}")
        elif src in domains and dst == "gxkit":
            breaks.append(f"{src!r} must not depend on the umbrella")
    return breaks


def main() -> int:
    modules, edges, domains = family_graph()
    breaks = check_layering(modules, edges)
    if breaks:
        for line in breaks:
            print(f"self: {line}")
        return 1
    source = build_artifact(modules, edges, domains)
    with tempfile.TemporaryDirectory(prefix="gxkit-self-") as directory:
        artifact = pathlib.Path(directory) / "module_graph.py"
        artifact.write_text(source, encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from gxkit.cli import main; raise SystemExit(main())",
                "inspect",
                str(artifact),
                "--json",
                "--no-storyboard",
                "--no-config",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    if result.returncode != 0:
        print(result.stdout + result.stderr)
        print("self: gxkit does not accept its own module graph")
        return 1
    print(f"self: {len(modules)} modules, {len(edges)} dependencies — the layering holds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
