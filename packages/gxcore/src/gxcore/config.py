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

from collections.abc import Iterable
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


def _names(value: object, *, where: str) -> set[str]:
    """A list of code names, or a located refusal.

    `ignore = "soft-lock"` is the mistake this exists for: iterating the string
    would silently mean the eight characters it contains, so a config that looks
    like it ignores one code would ignore nothing and the reader would not know.
    """
    if not isinstance(value, list) or not all(isinstance(name, str) for name in value):
        raise ValueError(f"{where}: expected a list of code names, not {value!r}")
    return set(value)


def _severities(value: object, *, where: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError(f"{where}: expected a table of code -> severity, not {value!r}")
    for code, severity in value.items():
        if not isinstance(severity, str) or severity not in VALID_SEVERITIES:
            raise ValueError(
                f"{where}.{code}: {severity!r} is not one of {', '.join(sorted(VALID_SEVERITIES))}"
            )
    return {str(code): str(severity) for code, severity in value.items()}


def load(start: str | Path, known_tools: Iterable[str] | None = None) -> Config:
    """The configuration for a directory, or empty.

    `known_tools` is what makes a *typo'd table name* refusable: `[chartgxx]` looks
    exactly like a tool table, so only a caller that knows the family can tell that
    it is inert — and a table that silently does nothing is the silent-narrowing
    failure this module refuses everywhere else. A single tool cannot judge that (a
    workspace file legitimately holds tables for its siblings), so it passes
    nothing and the umbrella passes the registry.
    """
    file = find(start)
    if file is None:
        return Config()
    data = tomllib.loads(file.read_text(encoding="utf-8"))
    where = str(file)
    unknown = sorted(
        set(data) - RESERVED - {name for name, value in data.items() if isinstance(value, dict)}
    )
    if unknown:
        raise ValueError(
            f"{where}: unrecognised key(s) {unknown}; expected {sorted(RESERVED)} or a tool table"
        )
    per_tool: dict[str, dict[str, Any]] = {}
    for name, value in data.items():
        if name in RESERVED or not isinstance(value, dict):
            continue
        if known_tools is not None and name not in known_tools:
            raise ValueError(
                f"{where}: [{name}] is not a tool; known tools are {sorted(known_tools)}"
            )
        extra = sorted(set(value) - RESERVED)
        if extra:
            # A mistyped `ignoer` would otherwise sit in the file looking active.
            raise ValueError(f"{where}: [{name}] has unrecognised key(s) {extra}")
        per_tool[name] = {
            "ignore": sorted(_names(value.get("ignore", []), where=f"{where}: [{name}] ignore")),
            "severity": _severities(value.get("severity", {}), where=f"{where}: [{name}] severity"),
        }
    return Config(
        ignore=_names(data.get("ignore", []), where=f"{where}: ignore"),
        severity=_severities(data.get("severity", {}), where=f"{where}: severity"),
        per_tool=per_tool,
    )


def apply(report: Report, config: Config, tool: str) -> Report:
    ignore, severity = config.for_tool(tool)
    if not ignore and not severity:
        return report
    for code, declared in severity.items():
        if not isinstance(declared, str) or declared not in VALID_SEVERITIES:
            # `Config` is public, so the value can also arrive without `load`.
            raise ValueError(
                f"config: {code!r} is set to {declared!r}, not one of "
                f"{', '.join(sorted(VALID_SEVERITIES))}"
            )
    kept = []
    for problem in report.problems:
        if problem.code in ignore:
            continue
        override = severity.get(problem.code)
        if override is not None:
            problem.severity = override
        kept.append(problem)
    report.problems = kept
    return report
