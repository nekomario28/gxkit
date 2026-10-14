"""Helpers that make "prove the check can fail" the cheapest thing to write.

A check that cannot fail is decoration. Every domain check should have one test
that builds the defect and asserts the problem fires, and — where the line
matters — one that asserts an honest artifact stays quiet.
"""

from __future__ import annotations

from collections.abc import Iterable

from .model import Report


def codes(report: Report) -> set[tuple[str, str]]:
    """The set of ``(severity, code)`` pairs in a report."""
    return {(p.severity, p.code) for p in report.problems}


def has(report: Report, code: str, severity: str | None = None) -> bool:
    if severity is None:
        return any(p.code == code for p in report.problems)
    return any(p.code == code and p.severity == severity for p in report.problems)


def assert_fires(report: Report, code: str, severity: str | None = None) -> None:
    if not has(report, code, severity):
        found = sorted(codes(report))
        raise AssertionError(f"expected {severity or 'any'}/{code} to fire; got {found}")


def assert_quiet(report: Report, code: str) -> None:
    if has(report, code):
        raise AssertionError(f"expected {code} not to fire")


def messages(report: Report) -> list[str]:
    return [p.message for p in report.problems]


def targets(report: Report, code: str) -> list[str | None]:
    return [p.target for p in report.problems if p.code == code]


def count(report: Report, code: str) -> int:
    return sum(1 for p in report.problems if p.code == code)


def missing(report: Report, expected: Iterable[str]) -> list[str]:
    return [c for c in expected if not has(report, c)]
