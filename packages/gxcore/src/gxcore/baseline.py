"""Compare a report to a stored baseline, so a re-run reports what changed.

A checker that always fails on pre-existing debt is one people switch off. A
*baseline* records the problems seen in an accepted state; the next run can then
report what is **new**, what **persisted**, and what was **fixed**, and gate only
on the new errors. This is the "keep history" half of the loop — commit the
baseline (`.gxkit-baseline.json`) and every run is a diff, not a fresh verdict.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .model import ERROR, Report

BASELINE_VERSION = 1
_SEP = "\x1f"


def fingerprint(code: str, target: str | None, label: str) -> str:
    """The identity of a problem across runs: code, target and label.

    Deliberately not the message (it carries numbers) and not the severity
    (`.gxkit.toml` may change it) — those are attributes, not identity.
    """
    return _SEP.join((code, target or "", label or ""))


def _record(problem: Any) -> dict[str, Any]:
    record: dict[str, Any] = {"code": problem.code, "severity": problem.severity}
    if problem.target:
        record["target"] = problem.target
    if problem.label:
        record["label"] = problem.label
    if problem.message:
        record["message"] = problem.message
    return record


def _key(record: dict[str, Any]) -> str:
    return fingerprint(record.get("code", ""), record.get("target"), record.get("label", ""))


@dataclass
class Baseline:
    name: str = ""
    problems: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def of(cls, report: Report) -> Baseline:
        return cls(name=report.name, problems=[_record(p) for p in report.sorted()])

    @classmethod
    def load(cls, path: str | Path) -> Baseline:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("version") != BASELINE_VERSION:
            raise ValueError(
                f"{path}: unsupported baseline version {data.get('version')!r} "
                f"(expected {BASELINE_VERSION})"
            )
        return cls(name=data.get("name", ""), problems=list(data.get("problems", [])))

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": BASELINE_VERSION, "name": self.name, "problems": self.problems}
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


@dataclass
class Diff:
    """What changed between a baseline and the current report."""

    new: list[Any] = field(default_factory=list)
    fixed: list[dict[str, Any]] = field(default_factory=list)
    persisted: list[Any] = field(default_factory=list)

    @property
    def new_errors(self) -> int:
        """Errors that are not in the baseline — the part that should fail a build."""
        return sum(1 for p in self.new if p.severity == ERROR)

    def as_dict(self) -> dict[str, int]:
        return {
            "new": len(self.new),
            "fixed": len(self.fixed),
            "persisted": len(self.persisted),
            "new_errors": self.new_errors,
        }


def compare(report: Report, baseline: Baseline) -> Diff:
    before = {_key(record): record for record in baseline.problems}
    after = {fingerprint(p.code, p.target, p.label): p for p in report.sorted()}
    return Diff(
        new=[p for key, p in after.items() if key not in before],
        fixed=[record for key, record in before.items() if key not in after],
        persisted=[p for key, p in after.items() if key in before],
    )


def summary(diff: Diff) -> str:
    """One block for the human report, old and new in the same breath."""
    head = (
        f"baseline: {len(diff.new)} new, {len(diff.fixed)} fixed, {len(diff.persisted)} unchanged"
    )
    if not diff.fixed:
        return head
    lines = [head, "  fixed:"]
    for record in diff.fixed:
        where = record.get("target") or "-"
        lines.append(f"    {record.get('severity', ''):<5} {where:<10} {record.get('code', '')}")
    return "\n".join(lines)
