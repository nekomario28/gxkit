"""apigx's domain knowledge: is this API contract safe and coherent?

The same graph questions as any contract — duplicates, dangling references — plus
the API-specific ones: a mutation with no authentication, a path outside the
versioned base, and an endpoint that documents no error.
"""

from __future__ import annotations

from gxcore import ERROR, INFO, WARN, Problem, Report

from .model import API
from .render import compute_layout, node_box


def _node_id(index: int) -> str:
    return f"ep[{index}]"


def inspect_api(api: API, name: str | None = None) -> Report:
    name = name or api.name
    report = Report(
        name=name,
        subject=f"api: {len(api.endpoints)} endpoints",
        details=[f"{len(api.endpoints)} endpoints", f"base: {api.base or '/'}"],
    )
    out: list[Problem] = []

    seen: dict[tuple[str, str], int] = {}
    for i, endpoint in enumerate(api.endpoints):
        target = _node_id(i)
        label = endpoint.label()
        key = (endpoint.verb, endpoint.path)
        if key in seen:
            out.append(
                Problem(
                    ERROR,
                    "duplicate-route",
                    f"{label} is declared twice",
                    target=target,
                    label=label,
                )
            )
        seen[key] = i
        if endpoint.mutating and not endpoint.auth:
            out.append(
                Problem(
                    ERROR,
                    "unauthenticated-mutation",
                    f"{label} changes state but requires no authentication",
                    target=target,
                    label=label,
                )
            )
        base = api.base.rstrip("/")
        under_base = endpoint.path == base or endpoint.path.startswith(base + "/")
        if api.base and not under_base:
            out.append(
                Problem(
                    WARN,
                    "path-outside-base",
                    f"{endpoint.path} is not under the base {api.base!r} (an unversioned path is one common case)",
                    target=target,
                    label=label,
                )
            )
        if not any(400 <= status < 600 for status in endpoint.statuses):
            out.append(
                Problem(
                    INFO,
                    "no-error-status",
                    f"{label} documents no error status (4xx/5xx)",
                    target=target,
                    label=label,
                )
            )
        if endpoint.deprecated:
            out.append(
                Problem(
                    INFO,
                    "deprecated-endpoint",
                    f"{label} is deprecated",
                    target=target,
                    label=label,
                )
            )

    if not api.endpoints:
        out.append(Problem(INFO, "no-endpoints", "the API declares no endpoints"))

    positions, r = compute_layout(api)
    for problem in out:
        if problem.bbox is None and problem.target in positions:
            problem.bbox = node_box(positions[problem.target], r)

    report.problems = out
    return report
