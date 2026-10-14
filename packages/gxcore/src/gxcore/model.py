"""The review loop's data model — shared by every `*gx` tool.

A `Problem` is one thing a reviewer would say about an artifact. A `Report` is
everything the reviewer found, plus a human summary of what was reviewed.

The contract an agent relies on:

  * every problem has a stable ``code`` (branch on it, never on prose),
  * a ``severity`` from a fixed three-level set,
  * ``error`` is the only severity that fails the build.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ERROR = "error"
WARN = "warn"
INFO = "info"

SEVERITIES = (ERROR, WARN, INFO)
_RANK = {ERROR: 0, WARN: 1, INFO: 2}

BBox = tuple[float, float, float, float]


def sort_key(p: Problem) -> tuple[int, str]:
    """Canonical problem order: errors first, then by target.

    The report and the storyboard both number problems in this order, so box
    ``[3]`` in the image is problem ``[3]`` in the text.
    """
    return (_RANK[p.severity], p.target or "")


@dataclass
class Problem:
    """One finding about an artifact."""

    severity: str
    code: str
    message: str
    target: str | None = None
    label: str = ""
    bbox: BBox | None = None

    def __post_init__(self) -> None:
        if self.severity not in _RANK:
            raise ValueError(f"unknown severity {self.severity!r}; use one of {SEVERITIES}")

    def as_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.target:
            d["target"] = self.target
        if self.label:
            d["label"] = self.label
        return d


@dataclass
class Report:
    """The result of inspecting one artifact."""

    name: str
    subject: str = ""
    details: list[str] = field(default_factory=list)
    problems: list[Problem] = field(default_factory=list)

    @property
    def errors(self) -> int:
        return sum(1 for p in self.problems if p.severity == ERROR)

    def sorted(self) -> list[Problem]:
        return sorted(self.problems, key=sort_key)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "subject": self.subject,
            "details": list(self.details),
            "errors": self.errors,
            "problems": [p.as_dict() for p in self.sorted()],
        }
