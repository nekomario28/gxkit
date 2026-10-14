"""seedgx's domain knowledge: is this run reproducible?

A run is reproducible when every stream is seeded with a real 32-bit value and no
two streams share a seed (shared seeds correlate their randomness).
"""

from __future__ import annotations

from gxcore import ERROR, INFO, WARN, Problem, Report

from .model import SEED_MAX, SeedSpec
from .render import compute_layout, node_box


def _node_id(index: int) -> str:
    return f"st[{index}]"


def inspect_spec(spec: SeedSpec, name: str | None = None) -> Report:
    name = name or spec.name
    report = Report(
        name=name,
        subject=f"seed: {len(spec.streams)} streams",
        details=[
            f"{len(spec.streams)} streams",
            "deterministic" if spec.deterministic else "not deterministic",
        ],
    )
    out: list[Problem] = []

    seen_names: set[str] = set()
    seen_seeds: dict[int, str] = {}
    for i, stream in enumerate(spec.streams):
        target = _node_id(i)
        if stream.name in seen_names:
            out.append(
                Problem(
                    ERROR,
                    "duplicate-stream",
                    f"stream {stream.name!r} is declared more than once",
                    target=target,
                    label=stream.name,
                )
            )
        seen_names.add(stream.name)
        if stream.seed is None:
            out.append(
                Problem(
                    ERROR,
                    "missing-seed",
                    f"stream {stream.name!r} has no seed — the run is not reproducible",
                    target=target,
                    label=stream.name,
                )
            )
        elif stream.seed < 0 or stream.seed > SEED_MAX:
            out.append(
                Problem(
                    ERROR,
                    "seed-out-of-range",
                    f"stream {stream.name!r} has seed {stream.seed}, outside 0..{SEED_MAX}",
                    target=target,
                    label=stream.name,
                )
            )
        else:
            if stream.seed in seen_seeds and seen_seeds[stream.seed] != stream.name:
                out.append(
                    Problem(
                        WARN,
                        "duplicate-seed",
                        f"stream {stream.name!r} reuses the seed of {seen_seeds[stream.seed]!r} "
                        "— their randomness is correlated",
                        target=target,
                        label=stream.name,
                    )
                )
            seen_seeds.setdefault(stream.seed, stream.name)

    if not spec.deterministic:
        out.append(Problem(INFO, "non-deterministic", "the manifest is marked non-deterministic"))
    if not spec.streams:
        out.append(Problem(INFO, "no-streams", "the manifest declares no streams"))

    positions, r = compute_layout(spec)
    for problem in out:
        if problem.bbox is None and problem.target in positions:
            problem.bbox = node_box(positions[problem.target], r)

    report.problems = out
    return report
