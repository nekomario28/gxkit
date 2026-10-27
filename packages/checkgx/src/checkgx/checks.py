"""checkgx's domain knowledge: can each check fail, and is it ever run?

Every problem here is one I hit while measuring a product: a check whose name was
written three times (a dict keeps one), a check that landed in the report's
metadata instead of the dict the runner reads, and names on both sides of the
declared/evaluated line that do not match. All three read as coverage and none of
them can fail.
"""

from __future__ import annotations

from gxcore import ERROR, WARN, Problem, Report

from .model import Registry


def inspect_registry(registry: Registry, name: str | None = None) -> Report:
    name = name or registry.name
    declared = registry.declared()
    evaluated = list(dict.fromkeys(registry.evaluated))
    metadata = list(dict.fromkeys(registry.metadata))
    report = Report(
        name=name,
        subject=f"checks: {len(declared)} declared, {len(evaluated)} evaluated",
        details=[
            f"{len(declared)} declared",
            f"{len(evaluated)} evaluated",
            f"{len(metadata)} metadata keys",
        ],
    )
    out: list[Problem] = []

    for check in declared:
        if declared[check] > 1:
            out.append(
                Problem(
                    ERROR,
                    "duplicate-check",
                    f"{check} is written {declared[check]} times; a mapping keeps one of them and the rest are never run",
                    label=check,
                )
            )
        if check in metadata:
            out.append(
                Problem(
                    ERROR,
                    "check-in-metadata",
                    f"{check} sits among the report's metadata, which the runner never evaluates",
                    label=check,
                )
            )
        elif check not in evaluated:
            out.append(
                Problem(
                    ERROR,
                    "check-never-evaluated",
                    f"{check} is declared but no evaluated mapping names it",
                    label=check,
                )
            )

    for check in evaluated:
        if check not in declared:
            out.append(
                Problem(
                    ERROR,
                    "evaluated-but-undeclared",
                    f"{check} is evaluated but never declared; a typo here silently drops a gate",
                    label=check,
                )
            )

    if not declared:
        out.append(Problem(ERROR, "no-checks", "the registry declares no checks at all"))
    elif not out:
        # Only when nothing else is wrong: a warning that always fires is a warning nobody reads.
        report.details.append("every check is declared once and evaluated")
        out.append(
            Problem(
                WARN,
                "not-a-proof-of-failure",
                "this reads the registry, not the predicates: a check that cannot fail inside its body is invisible here",
                label=name,
            )
        )
    report.problems = out
    return report
