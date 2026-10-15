"""Inspect real artifacts after a cold, isolated uv tool install of a Git SHA.

The CLI comes from the installed distribution, never the workspace interpreter.
Direct-URL metadata binds the consumer to the requested immutable revision.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path


class Consumer:
    def __init__(self, root: Path, env: dict[str, str]) -> None:
        self.root = root
        self.env = env
        self.cli = root / "bin/gxkit"

    def inspect(self, path: Path, expected: int, *flags: str) -> dict:
        result = subprocess.run(
            [
                str(self.cli),
                "inspect",
                str(path),
                "--json",
                "--no-storyboard",
                "--no-config",
                *flags,
            ],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == expected, (
            f"{path.name}: expected {expected}, got {result.returncode}: {result.stdout} {result.stderr}"
        )
        assert "Traceback" not in result.stderr
        print(f"consumer: {path.name} -> {expected}", flush=True)
        return json.loads(result.stdout) if expected != 2 else {}

    def artifact(self, name: str, source: str) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        return path

    def verify(self) -> None:
        clean = self.artifact("clean.py", 'STREAMS = [("python",0),("numpy",4294967295)]\n')
        assert self.inspect(clean, 0)["errors"] == 0
        self.inspect(self.artifact("bad_member.py", 'RUNS = [("good",0,1),{}]\n'), 2)
        self.inspect(self.artifact("fractional.py", 'STREAMS = [("bad",-0.5)]\n'), 2)
        zero = self.artifact(
            "empty_interval.py", 'RUNS = [("active",0,10,"r"),("empty",5,0,"r")]\n'
        )
        assert [p["code"] for p in self.inspect(zero, 0)["problems"]] == ["zero-duration"]
        nan = self.artifact("nonfinite.py", 'RUNS = [("bad",0,float("nan"),"r")]\n')
        assert [p["code"] for p in self.inspect(nan, 1)["problems"]] == ["non-finite-time"]
        exiting = self.artifact("gates/a.py", "raise SystemExit(0)\n")
        self.inspect(exiting, 2)
        self.artifact("gates/b.py", 'STREAMS = [("bad",None)]\n')
        directory = subprocess.run(
            [str(self.cli), "inspect", str(exiting.parent), "--no-config", "--no-storyboard"],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert directory.returncode == 2 and "missing-seed" in directory.stdout
        print("consumer: directory exit cannot bypass later findings", flush=True)
        baseline = self.root / "baseline.json"
        before = self.artifact(
            "before.py", 'RUNS = [("a",0,10,"r"),("b",30,10,"r"),("c",5,10,"r")]\n'
        )
        self.inspect(before, 1, "--write-baseline", str(baseline))
        added = self.artifact(
            "added.py", 'RUNS = [("a",0,10,"r"),("b",12,10,"r"),("c",5,10,"r")]\n'
        )
        assert self.inspect(added, 1, "--baseline", str(baseline))["baseline"] == {
            "new": 1,
            "fixed": 0,
            "persisted": 1,
            "new_errors": 1,
        }
        replaced = self.artifact(
            "replaced.py", 'RUNS = [("a",30,10,"r"),("b",0,10,"r"),("c",5,10,"r")]\n'
        )
        assert self.inspect(replaced, 1, "--baseline", str(baseline))["baseline"] == {
            "new": 1,
            "fixed": 1,
            "persisted": 0,
            "new_errors": 1,
        }
        # A replaced unknown endpoint is new debt, not unchanged debt.
        net_baseline = self.root / "net-baseline.json"
        net_before = self.artifact(
            "net_before.py",
            'NODES = {"known": "service"}\nEDGES = [("known", "missing_a")]\n',
        )
        self.inspect(net_before, 1, "--write-baseline", str(net_baseline))
        net_after = self.artifact(
            "net_after.py",
            'NODES = {"known": "service"}\nEDGES = [("known", "missing_b")]\n',
        )
        report = self.inspect(net_after, 1, "--baseline", str(net_baseline))
        assert report["baseline"]["new_errors"] == 1, report["baseline"]
        print("consumer: a replaced edge endpoint is a new error", flush=True)
        # An artifact's own directory change must not redirect the inspection.
        relative = self.root / "relative"
        (relative / "elsewhere").mkdir(parents=True)
        (relative / "artifact.py").write_text(
            'import os\nSTREAMS = [("bad", None)]\nos.chdir("elsewhere")\n', encoding="utf-8"
        )
        (relative / "elsewhere" / "artifact.py").write_text(
            'STREAMS = [("good", 1)]\n', encoding="utf-8"
        )
        moved = subprocess.run(
            [str(self.cli), "inspect", "artifact.py", "--no-config", "--no-storyboard"],
            cwd=relative,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert moved.returncode == 1 and "missing-seed" in moved.stdout, moved.stdout
        print("consumer: a relative input survives the artifact changing directory", flush=True)
        # A later invocation executes again, but detection cannot execute twice.
        counter = self.root / "counter"
        once = self.artifact(
            "once.py",
            "from pathlib import Path\n"
            + f"p=Path({str(counter)!r})\n"
            + 'p.write_text(str(int(p.read_text(encoding="utf-8"))+1) if p.exists() else "1", encoding="utf-8")\nSTREAMS=[("ok",1)]\n',
        )
        self.inspect(once, 0)
        assert counter.read_text(encoding="utf-8") == "1"
        self.inspect(once, 0)
        assert counter.read_text(encoding="utf-8") == "2"


def readme_entrance(root: Path, env: dict[str, str]) -> None:
    """Run the single-tool entrance the README documents, exactly as written.

    The README's first command is the one a reader with a single artifact runs,
    so it is executed with a fresh tool directory rather than trusted: a
    documented command that cannot run is the defect this gate exists to catch.
    """
    import re

    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    anchor = readme.find("Install the one tool you need")
    assert anchor >= 0, "the README no longer documents a single-tool installation"
    block = re.search(r"```sh\n(?P<body>.*?)\n```", readme[anchor:], re.S)
    assert block, "the documented installation has no shell block"
    lines = [line.strip() for line in block.group("body").splitlines() if line.strip()]
    assert len(lines) == 2, f"the documented entrance changed shape: {lines}"
    install, command = (shlex.split(line) for line in lines)
    assert install[:3] == ["uv", "tool", "install"], lines[0]
    uv = shutil.which("uv")
    assert uv, "uv is required to run the documented entrance"
    # The command names a placeholder file, so give it the artifact it implies.
    (root / command[-1]).write_text(
        "import matplotlib.pyplot as plt\n\nfig, ax = plt.subplots()\n",
        encoding="utf-8",
    )
    # `uv tool install` puts the command in the fresh bin directory, so it has to
    # be on PATH for the documented follow-up command to resolve — otherwise a
    # developer's own install would silently satisfy this, which is the defect
    # this gate was written for.
    entrance_env = {
        **env,
        "PATH": os.pathsep.join([env["UV_TOOL_BIN_DIR"], env.get("PATH", "")]),
    }
    for argv in ([uv, *install[1:]], command):
        result = subprocess.run(
            argv,
            cwd=root,
            env=entrance_env,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        assert result.returncode in {0, 1}, f"{' '.join(argv)}: {result.stdout}{result.stderr}"
    print(f"consumer: the README entrance runs as written ({' '.join(command)})", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True, help="full immutable Git commit SHA")
    parser.add_argument(
        "--repository",
        default="https://github.com/nekomario28/gxkit",
        help="Git URL or local checkout (CI)",
    )
    args = parser.parse_args(argv)
    assert re.fullmatch(r"[0-9a-f]{40}", args.revision), "consumer verification requires a full SHA"
    uv = shutil.which("uv")
    assert uv, "uv is required for the documented consumer install route"
    repository = (
        args.repository if "://" in args.repository else Path(args.repository).resolve().as_uri()
    )
    source = f"git+{repository}@{args.revision}#subdirectory=packages/gxkit"
    with tempfile.TemporaryDirectory(prefix="gxkit-consumer-") as directory:
        root = Path(directory)
        env = {
            **os.environ,
            "UV_TOOL_DIR": str(root / "tools"),
            "UV_TOOL_BIN_DIR": str(root / "bin"),
            "UV_CACHE_DIR": str(root / "cache"),
        }
        for key in (
            "PYTHONPATH",
            "PYTHONHOME",
            "VIRTUAL_ENV",
            "UV_NO_SOURCES",
            "UV_PROJECT_ENVIRONMENT",
        ):
            env.pop(key, None)
        install = subprocess.run(
            [uv, "tool", "install", source],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=240,
            check=False,
        )
        assert install.returncode == 0, install.stdout + install.stderr
        python = root / "tools/gxkit-cli/bin/python"
        evidence = subprocess.run(
            [
                str(python),
                "-c",
                'import importlib.metadata as m, json; print(json.loads(m.distribution("gxkit-cli").read_text("direct_url.json"))["vcs_info"]["commit_id"])',
            ],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert evidence.returncode == 0 and evidence.stdout.strip() == args.revision, (
            evidence.stdout + evidence.stderr
        )
        print(f"consumer: installed {args.revision} in isolated tool/cache directories", flush=True)
        Consumer(root, env).verify()
        readme_entrance(root, env)
    print("Consumer inspection gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
