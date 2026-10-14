"""A random-seed manifest: one seed per randomness stream, for reproducibility.

    import seedgx as s

    spec = s.SeedSpec(
        streams=[s.Stream("python", 42), s.Stream("numpy", 7)],
        deterministic=True,
    )

This manifest checks declarations, not runtime reproducibility. Seeds must be
integers in the unsigned 32-bit range; their meaning depends on the RNG.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from gxcore.loading import InvalidArtifact, convert_items

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


def _seed(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidArtifact("seed: expected an integer or None (no coercion)")
    return value


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
        return Stream(str(name), _seed(seed))
    if isinstance(value, (tuple, list)) and value:
        if len(value) > 2:
            return None
        seed = value[1] if len(value) > 1 else None
        return Stream(str(value[0]), _seed(seed))
    return None


def _as_spec(value: object) -> SeedSpec | None:
    if isinstance(value, SeedSpec):
        value.streams = convert_items(value.streams, _as_stream, field="streams")
        return value
    if isinstance(value, dict) and "streams" in value:
        return SeedSpec(
            streams=convert_items(value["streams"], _as_stream, field="streams"),
            deterministic=bool(value.get("deterministic", True)),
            name=str(value.get("name", "seed")),
        )
    if isinstance(value, (list, tuple)):
        return SeedSpec(streams=convert_items(value, _as_stream, field="streams"))
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
                streams=convert_items(streams, _as_stream, field="STREAMS"),
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
