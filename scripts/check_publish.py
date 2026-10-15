"""Prove the family installs from an index, before anything is published.

The Git consumer route installs from a checkout, so it cannot catch a dependency
range only an index resolver would reject. This builds every distribution, serves
them from a local PEP 503 index, and installs the umbrella against that index
alone with workspace sources disabled — the same resolution a PyPI install would
perform, with nothing published.

Third-party dependencies (Pillow, matplotlib, moderngl, numpy) may come from
PyPI; the family's own packages may not.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UMBRELLA = "gxkit-cli"

OPENAPI = {
    "openapi": "3.0.3",
    "info": {"title": "Payments"},
    "servers": [{"url": "https://api.example.com/v1"}],
    "paths": {"/v1/charge": {"post": {"security": [], "responses": {"201": {}}}}},
}

SQL = """CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL
);

CREATE TABLE posts (
    id BIGSERIAL PRIMARY KEY,
    author_id INTEGER,
    FOREIGN KEY (author_id) REFERENCES users (email)
);
"""

MERMAID = """stateDiagram-v2
    [*] --> cart
    cart --> paid : pay
    paid --> [*]
    abandoned --> cart : resume
"""


def _family_names() -> set[str]:
    try:
        import tomllib
    except ModuleNotFoundError:  # Python 3.10
        import tomli as tomllib

    names = set()
    for pyproject in sorted((ROOT / "packages").glob("*/pyproject.toml")):
        project = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]
        names.add(project["name"])
    return names


def _build(dist: Path) -> list[Path]:
    result = subprocess.run(
        [*_uv(), "build", "--all-packages", "-o", str(dist)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    wheels = sorted(dist.glob("*.whl"))
    assert len(wheels) == len(_family_names()), (
        f"expected one wheel per package, found {len(wheels)} of {len(_family_names())}"
    )
    return wheels


def _uv() -> list[str]:
    uv = shutil.which("uv")
    assert uv, "uv is required for the documented install route"
    return [uv]


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _index(dist: Path, index: Path) -> Path:
    """A minimal PEP 503 index: one directory per project, listing its wheels."""
    index.mkdir(parents=True, exist_ok=True)
    for wheel in sorted(dist.glob("*.whl")):
        project = _normalize(wheel.name.split("-")[0])
        directory = index / project
        directory.mkdir(exist_ok=True)
        shutil.copyfile(wheel, directory / wheel.name)
        links = sorted(p.name for p in directory.glob("*.whl"))
        body = "<!DOCTYPE html><html><body>\n" + "".join(
            f'<a href="{html.escape(name)}">{html.escape(name)}</a><br/>\n' for name in links
        )
        (directory / "index.html").write_text(body + "</body></html>\n", encoding="utf-8")
    return index


def _install(index: Path, root: Path) -> Path:
    """Install the umbrella the way a family reader would."""
    env = _install_env(index, root)
    result = subprocess.run(
        [
            *_uv(),
            "tool",
            "install",
            UMBRELLA,
            "--index-strategy",
            "unsafe-best-match",
            "--reinstall",
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return root / "bin/gxkit"


def _install_env(index: Path, root: Path) -> dict[str, str]:
    """A tool environment that resolves the family from the local index.

    Third-party dependencies (Pillow, matplotlib, moderngl, numpy) still come
    from PyPI; the family's own packages must not, and the workspace must not
    shadow them — which is the mistake a Git install cannot catch.
    """
    env = {
        **os.environ,
        "UV_TOOL_DIR": str(root / "tools"),
        "UV_TOOL_BIN_DIR": str(root / "bin"),
        "UV_CACHE_DIR": str(root / "cache"),
        "UV_INDEX": index.as_uri(),
        "UV_FIND_LINKS": index.as_uri(),
    }
    for key in (
        "PYTHONPATH",
        "PYTHONHOME",
        "VIRTUAL_ENV",
        "UV_PROJECT_ENVIRONMENT",
        "UV_INDEX_URL",
        "UV_DEFAULT_INDEX",
    ):
        env.pop(key, None)
    return env


def _install_tool(index: Path, root: Path, name: str) -> None:
    """Install one tool the way a single-purpose reader would."""
    result = subprocess.run(
        [*_uv(), "tool", "install", name],
        cwd=root,
        env=_install_env(index, root),
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _installed_versions(tools: Path) -> dict[str, str]:
    python = tools / UMBRELLA / "bin/python"
    assert python.exists(), f"no interpreter at {python}"
    result = subprocess.run(
        [
            str(python),
            "-c",
            "import importlib.metadata as m, json;"
            "print(json.dumps({d.metadata['Name']: d.version for d in m.distributions()}))",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    installed: dict[str, str] = json.loads(result.stdout)
    return {key.lower(): value for key, value in installed.items()}


def _run(cli: Path, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("UV_", "PYTHONPATH"))}
    return subprocess.run(
        [str(cli), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-build", action="store_true", help="reuse an existing dist/ (for local runs)"
    )
    args = parser.parse_args(argv)
    family = _family_names()
    with tempfile.TemporaryDirectory(prefix="gxkit-publish-") as directory:
        root = Path(directory)
        dist = root / "dist"
        dist.mkdir()
        if args.skip_build:
            for wheel in sorted((ROOT / "dist").glob("*.whl")):
                shutil.copyfile(wheel, dist / wheel.name)
        else:
            _build(dist)
        index = _index(dist, root / "index")
        cli = _install(index, root)
        installed = _installed_versions(root / "tools")
        missing = {name for name in family if name not in installed}
        assert not missing, f"the family did not resolve from the index: {sorted(missing)}"
        print(
            f"publish: {len(installed)} distributions resolved from a local index "
            f"({', '.join(sorted(name for name in family if name in installed))})",
            flush=True,
        )
        artifact = root / "chart.py"
        artifact.write_text(
            "import matplotlib.pyplot as plt\n\nfig, ax = plt.subplots()\nax.bar(['a'], [1])\n",
            encoding="utf-8",
        )
        clean = _run(
            cli, root, "inspect", str(artifact), "--json", "--no-storyboard", "--no-config"
        )
        assert clean.returncode in {0, 1}, clean.stdout + clean.stderr
        payload = json.loads(clean.stdout)
        assert payload["errors"] == 0, payload
        listed = _run(cli, root, "tools", "--json")
        assert listed.returncode == 0, listed.stderr
        tools = {entry["name"] for entry in json.loads(listed.stdout)}
        assert tools == {name for name in family if name not in {"gxcore", "gxkit-cli"}}, tools
        for command, expected in (("tools", 0), ("codes", 0)):
            assert _run(cli, root, command).returncode == expected
        # A reader installs the one tool they need, so each tool's own console
        # script must work from the index — the umbrella's routing does not prove
        # that. `uv tool install` takes one requirement, which is also exactly
        # what that reader does.
        for name in sorted(tools):
            _install_tool(index, root, name)
            binary = root / "bin" / name
            assert binary.exists(), f"{name}: the index install has no {name} console script"
            version = _run(binary, root, "--version")
            assert version.returncode == 0, f"{name} --version: {version.stderr}"
            print(f"publish: {name} installed from the index and ran", flush=True)
        # And the entrances the README advertises must work with a document the
        # reader already has, not only with a Python declaration.
        (root / "openapi.json").write_text(json.dumps(OPENAPI), encoding="utf-8")
        (root / "schema.sql").write_text(SQL, encoding="utf-8")
        (root / "checkout.mmd").write_text(MERMAID, encoding="utf-8")
        for name, document, code in (
            ("apigx", "openapi.json", "unauthenticated-mutation"),
            ("schemagx", "schema.sql", "fk-to-non-primary-key"),
            ("flowgx", "checkout.mmd", "unreachable-state"),
        ):
            inspected = _run(
                root / "bin" / name,
                root,
                "inspect",
                document,
                "--json",
                "--no-storyboard",
                "--no-config",
            )
            # The verdict's severity depends on the document; what must hold is
            # that this command, from this install, reports this finding.
            assert inspected.returncode in {0, 1}, f"{name} {document}: {inspected.stdout}"
            reported = {problem["code"] for problem in json.loads(inspected.stdout)["problems"]}
            assert code in reported, f"{name} {document}: {sorted(reported)}"
            print(f"publish: {name} inspect {document} -> {code}", flush=True)
        print("publish: the installed umbrella routes every tool and inspects an artifact")
    print("Index installation gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
