"""Every problem code the family can emit — as data, not prose.

`gxkit codes` reads this; a test scans the source and fails if a `Problem(...)`
literal is not listed here, so the catalogue cannot quietly drift.
"""

from __future__ import annotations

CODEBOOK: dict[str, dict[str, str]] = {
    "gxcore": {  # emitted by shared components (gxcore.layout)
        "clipped-text": "error",
        "text-overlap": "error",
        "small-text": "info",
    },
    "chartgx": {
        "truncated-baseline": "error",
        "empty-chart": "error",
        "log-nonpositive": "error",
        "clipped-text": "error",
        "text-overlap": "error",
        "no-title": "warn",
        "no-xlabel": "warn",
        "no-ylabel": "warn",
        "dual-axis": "warn",
        "too-many-series": "warn",
        "pie-slices": "warn",
        "constant-series": "warn",
        "clipped-data": "warn",
        "legend-covers": "warn",
        "inverted-axis": "warn",
        "small-text": "info",
        "no-units": "info",
        "cut-value-axis": "info",
        "red-green": "info",
    },
    "levelgx": {
        "no-spawn": "error",
        "no-goal": "error",
        "goal-unreachable": "error",
        "soft-lock": "error",
        "stranded-item": "error",
        "hazard-cuts-off": "warn",
        "unreachable-area": "info",
        "no-items": "info",
    },
    "flowgx": {
        "no-start": "error",
        "no-accept": "error",
        "unknown-state": "error",
        "unreachable-state": "error",
        "dead-end": "error",
        "no-exit": "error",
        "ambiguous-transition": "error",
        "cycle": "info",
        "clipped-text": "error",
        "text-overlap": "error",
        "small-text": "info",
    },
    "protogx": {
        "no-start": "error",
        "unknown-state": "error",
        "unknown-message": "error",
        "unhandled-message": "error",
        "nondeterministic": "error",
        "deadlock": "error",
        "no-exit": "error",
        "unreachable-state": "error",
        "no-terminal": "error",
        "missing-response": "warn",
        "cycle": "info",
    },
    "authzgx": {
        "escalation": "error",
        "cyclic-inheritance": "error",
        "dangling-grant": "error",
        "dangling-assignment": "error",
        "dangling-inherit": "error",
        "unreachable-role": "info",
        "orphan-permission": "info",
        "unreachable-permission": "info",
        "empty-role": "info",
        "no-sensitive": "info",
        "no-low": "info",
        "no-permissions": "info",
    },
    "depsgx": {
        "cycle": "error",
        "layer-violation": "error",
        "forbidden-dependency": "error",
        "self-dependency": "error",
        "dangling-dependency": "error",
        "unreachable-module": "info",
        "orphan-module": "info",
        "duplicate-dependency": "info",
        "no-roots": "info",
    },
    "schemagx": {
        "dangling-foreign-key": "error",
        "fk-type-mismatch": "warn",
        "fk-to-non-primary-key": "warn",
        "cyclic-foreign-key": "warn",
        "missing-primary-key": "info",
        "orphan-table": "info",
        "no-tables": "info",
    },
    "docgx": {
        "clipped-text": "error",
        "text-overlap": "error",
        "no-title": "warn",
        "too-much-text": "warn",
        "small-text": "info",
        "reading-order": "info",
        "empty-page": "info",
    },
    "shadergx": {
        "compile-error": "error",
        "bad-size": "error",
        "nan-output": "error",
        "black-output": "error",
        "constant-output": "warn",
        "uniform-unused": "warn",
        "nondeterministic": "info",
    },
    "framegx": {
        "missing-file": "error",
        "probe-error": "error",
        "no-frames": "error",
        "all-black": "error",
        "frozen": "error",
        "single-color": "warn",
        "no-motion": "warn",
        "duration-mismatch": "warn",
        "wrong-fps": "warn",
        "wrong-size": "warn",
        "no-audio": "warn",
        "silent-audio": "warn",
    },
    "apigx": {
        "duplicate-route": "error",
        "unauthenticated-mutation": "error",
        "unversioned-path": "warn",
        "no-error-status": "info",
        "deprecated-endpoint": "info",
        "no-endpoints": "info",
    },
    "netgx": {
        "dangling-edge": "error",
        "public-reaches-sensitive": "error",
        "self-loop": "warn",
        "duplicate-edge": "info",
        "isolated-node": "info",
        "no-public": "info",
    },
}


def for_tool(name: str) -> dict[str, str]:
    return dict(CODEBOOK.get(name, {}))


def flat() -> dict[str, list[str]]:
    """code -> tools that can emit it."""
    out: dict[str, list[str]] = {}
    for tool, codes in CODEBOOK.items():
        for code in codes:
            out.setdefault(code, []).append(tool)
    return {code: sorted(tools) for code, tools in sorted(out.items())}
