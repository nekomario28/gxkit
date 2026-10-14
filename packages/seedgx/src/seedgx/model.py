"""A random-seed manifest: one seed per randomness stream, for reproducibility.

    import seedgx as s

    spec = s.SeedSpec(
        streams=[s.Stream("python", 42), s.Stream("numpy", 7)],
        deterministic=True,
    )

A run is reproducible when every stream is seeded, no two streams share a seed,
and the seed is a real 32-bit value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

SEED_MAX = 2**32 - 1


@dataclass
class Stream:
    name: str
    seed: int | None = None


@dataclass
class SeedSpec:
    streams: list[Stream] = field(default_factory=list)
    deterministic: bool = True
    name: str = "seed"

    def names(self) -> list[str]:
        return [stream.name for stream in self.streams]


def _as_stream(value: object) -> Stream | None:
    if isinstance(value, Stream):
        return value
    if isinstance(value, str):
        return Stream(value)
    if isinstance(value, dict):
        name = value.get("name")
        if name is None:
            return None
        seed = value.get("seed")
        return Stream(str(name), int(seed) if seed is not None else None)
    if isinstance(value, (tuple, list)) and value:
        seed = value[1] if len(value) > 1 else None
        return Stream(str(value[0]), int(seed) if seed is not None else None)
    return None


def _as_spec(value: object) -> SeedSpec | None:
    if isinstance(value, SeedSpec):
        return value
    if isinstance(value, dict) and "streams" in value:
        streams = [_as_stream(item) for item in value["streams"]]
        if any(stream is None for stream in streams):
            return None
        return SeedSpec(
            streams=[stream for stream in streams if stream is not None],
            deterministic=bool(value.get("deterministic", True)),
            name=str(value.get("name", "seed")),
        )
    if isinstance(value, (list, tuple)):
        built: list[Stream] = []
        for item in value:
            stream = _as_stream(item)
            if stream is None:
                return None
            built.append(stream)
        if built:
            return SeedSpec(streams=built)
    return None


def load_spec(path: str | Path) -> tuple[SeedSpec, object]:
    from gxcore.loading import load_module, resolve

    path = Path(path)
    module = load_module(path)
    spec = resolve(
        module,
        attrs=("seed", "SEED", "spec", "manifest", "seeds"),
        builders=("build", "make_seed", "make"),
        convert=_as_spec,
    )
    if spec is None:
        streams = getattr(module, "STREAMS", None)
        if streams is not None:
            spec = SeedSpec(
                streams=[s for s in (_as_stream(item) for item in streams) if s is not None],
                deterministic=bool(getattr(module, "DETERMINISTIC", True)),
            )
    if spec is None:
        raise ValueError(f"{path}: no seed manifest found — define `spec` (a SeedSpec) or STREAMS")
    spec.name = getattr(module, "NAME", path.stem)
    return spec, module


def spec_from_parts(
    streams: list[Stream] | None = None,
    deterministic: bool = True,
    name: str = "seed",
) -> SeedSpec:
    return SeedSpec(streams=list(streams or []), deterministic=deterministic, name=name)
