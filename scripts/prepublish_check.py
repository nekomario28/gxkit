#!/usr/bin/env python3
"""Pre-publication check for this repository.

Fails (exit 1) if a tracked file carries a credential or a machine-specific
home path, so the rule is runnable evidence rather than prose. Run before
making the repository public or cutting a release:

    python scripts/prepublish_check.py

It also prints the commit authors so an unexpected external author or a
`Co-authored-by:` trailer is visible.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

SECRETS: list[tuple[str, re.Pattern[str]]] = [
    ("aws-access-key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github-token", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("openai-key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9-]{20,}\b")),
    ("slack-token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("private-key-block", re.compile(r"BEGIN [A-Z ]*PRIVATE KEY")),
    (
        "hardcoded-secret",
        re.compile(
            r"(?i)(api[_-]?key|secret|passwd|password|access[_-]?token)\s*[:=]\s*['\"][^'\"]{12,}['\"]"
        ),
    ),
]

MACHINE_PATHS: list[tuple[str, re.Pattern[str]]] = [
    ("unix-home-path", re.compile(r"/(?:home|Users)/[A-Za-z0-9._-]+/")),
    ("windows-home-path", re.compile(r"[A-Za-z]:\\\\?Users\\\\?[A-Za-z0-9._-]+")),
]


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], capture_output=True, check=True).stdout
    return [p for p in out.decode().split("\x00") if p]


def scan_head() -> list[tuple[str, str, int, str]]:
    findings: list[tuple[str, str, int, str]] = []
    for name in tracked_files():
        try:
            text = pathlib.Path(name).read_text(encoding="utf-8")
        except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for rule, rx in SECRETS + MACHINE_PATHS:
                if rx.search(line):
                    findings.append((rule, name, lineno, line.strip()[:120]))
    return findings


def scan_history() -> tuple[list[tuple[str, str, int, str]], list[tuple[str, str, int, str]]]:
    """(secrets, machine_paths) found in added lines anywhere in history."""
    diff = subprocess.run(
        ["git", "log", "-p", "--all", "--no-color"], capture_output=True, text=True
    ).stdout
    secrets: list[tuple[str, str, int, str]] = []
    paths: list[tuple[str, str, int, str]] = []
    for line in diff.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        for rule, rx in SECRETS:
            if rx.search(line):
                secrets.append((rule, "(history)", 0, line[1:].strip()[:120]))
        for rule, rx in MACHINE_PATHS:
            if rx.search(line):
                paths.append((rule, "(history)", 0, line[1:].strip()[:120]))
    return secrets, paths


def main() -> int:
    head = scan_head()
    history_secrets, history_paths = scan_history()
    fatal = head + history_secrets

    if fatal:
        print("PREPUBLICATION: FAIL")
        for rule, name, lineno, line in fatal:
            print(f"  {rule}: {name}:{lineno}: {line}")
    else:
        print("PREPUBLICATION: CLEAN — no credentials or machine paths in the working tree")

    if history_paths:
        print("PREPUBLICATION: WARN — machine paths remain in history (rewrite it to remove them):")
        for rule, name, _, line in history_paths[:5]:
            print(f"  {rule}: {name}: {line}")

    authors = sorted(set(_git("log", "--format=%an <%ae>").splitlines()))
    print("authors:", "; ".join(authors) or "none")
    trailers = [
        ln.strip()
        for ln in _git("log", "--format=%B").splitlines()
        if re.search(r"(?i)co-authored-by|signed-off-by", ln)
    ]
    print("trailers:", "; ".join(sorted(set(trailers))) or "none")
    submodules = pathlib.Path(".gitmodules").exists()
    print("submodules:", "present" if submodules else "none")

    return 1 if fatal else 0


if __name__ == "__main__":
    sys.exit(main())
