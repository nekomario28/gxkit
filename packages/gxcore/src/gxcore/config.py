"""Per-project configuration: ignore a code, or change its severity.

A `.gxkit.toml` anywhere up the tree from the artifact is read by every tool:

    # ignore a note everywhere
    ignore = ["no-units"]

    # treat this warning as an error
    [severity]
    dual-axis = "error"

    # ...or only for one tool
    [chartgx]
    ignore = ["red-green"]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover  (Python 3.10 only)
    import tomli as tomllib

from .model import Report

VALID_SEVERITIES = {"error", "warn", "info"}
RESERVED = {"ignore", "severity"}


@dataclass
class Config:
    ignore: set[str] = field(default_factory=set)
    severity: dict[str, str] = field(default_factory=dict)
    per_tool: dict[str, dict[str, Any]] = field(default_factory=dict)

    def for_tool(self, tool: str) -> tuple[set[str], dict[str, str]]:
        ignore = set(self.ignore)
        severity = dict(self.severity)
        section = self.per_tool.get(tool, {})
        ignore |= set(section.get("ignore", []))
        severity.update(section.get("severity", {}))
        return ignore, severity


def find(start: str | Path) -> Path | None:
    """The nearest `.gxkit.toml` from ``start`` up to the repository root."""
    path = Path(start).resolve()
    for directory in [path, *path.parents]:
        candidate = directory / ".gxkit.toml"
        if candidate.is_file():
            return candidate
        if (directory / ".git").exists():
            break
    return None


def load(start: str | Path) -> Config:
    file = find(start)
    if file is None:
        return Config()
    data = tomllib.loads(file.read_text(encoding="utf-8"))
    per_tool = {k: v for k, v in data.items() if k not in RESERVED and isinstance(v, dict)}
    return Config(
        ignore=set(data.get("ignore", [])),
        severity={k: v for k, v in data.get("severity", {}).items()},
        per_tool=per_tool,
    )


def apply(report: Report, config: Config, tool: str) -> Report:
    ignore, severity = config.for_tool(tool)
    if not ignore and not severity:
        return report
    kept = []
    for problem in report.problems:
        if problem.code in ignore:
            continue
        override = severity.get(problem.code)
        if override in VALID_SEVERITIES:
            problem.severity = override
        kept.append(problem)
    report.problems = kept
    return report
