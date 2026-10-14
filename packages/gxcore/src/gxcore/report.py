"""Print a report the way an agent and a person each need it.

The human form mirrors `manimgx inspect`: a header, the summary of what was
reviewed, then numbered problems. The JSON form is the same report for a tool.
"""

from __future__ import annotations

import json
from pathlib import Path

from .model import Report


def human(source: str | Path, report: Report, storyboard: str | Path | None = None) -> str:
    src = Path(source).name
    lines = [f"{src}: {report.name}"]
    if report.subject:
        lines.append(report.subject)
    if storyboard is not None:
        lines.append(f"storyboard: {Path(storyboard).name}")
    lines += [f"  {d}" for d in report.details]

    problems = report.sorted()
    if not problems:
        lines.append("inspect: no problems")
        return "\n".join(lines)

    n, e = len(problems), report.errors
    lines.append(f"inspect: {n} problem{'s' if n != 1 else ''} ({e} error{'s' if e != 1 else ''})")
    for i, p in enumerate(problems, start=1):
        where = p.target or "-"
        lines.append(f"  [{i}] {p.severity:<5} {where:<10} {p.code}: {p.message}")
    return "\n".join(lines)


def to_json(report: Report, storyboard: str | Path | None = None) -> str:
    payload = report.as_dict()
    if storyboard is not None:
        payload["storyboard"] = str(storyboard)
    return json.dumps(payload, indent=2, ensure_ascii=False)
