"""An HTTP API contract, declared as data.

    import apigx as a

    api = a.API(
        base="/v1",
        endpoints=[
            a.Endpoint("GET", "/v1/users", statuses=[200, 404]),
            a.Endpoint("POST", "/v1/users", auth=True, statuses=[201, 400]),
        ],
    )

An `Endpoint` is a method and a path, plus whether it requires authentication,
the status codes it documents, and whether it is deprecated. A mutating method
(POST/PUT/PATCH/DELETE) with `auth=False` is a real bug.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from gxcore.loading import convert_items, convert_names

MUTATING = {"POST", "PUT", "PATCH", "DELETE"}


@dataclass
class Endpoint:
    method: str
    path: str
    auth: bool = True
    #: Numeric statuses, plus the ranged keys (`"5XX"`) and `"default"` as written:
    #: a range is not a number, and dropping it made `no-error-status` fire on an
    #: operation that documents its errors.
    statuses: list[int | str] = field(default_factory=list)
    deprecated: bool = False

    @property
    def verb(self) -> str:
        return self.method.upper()

    @property
    def mutating(self) -> bool:
        return self.verb in MUTATING

    def label(self) -> str:
        return f"{self.verb} {self.path}"


@dataclass
class API:
    endpoints: list[Endpoint] = field(default_factory=list)
    base: str = "/v1"
    name: str = "api"
    auth_schemes: list[str] = field(default_factory=list)

    def routes(self) -> list[tuple[str, str]]:
        return [(e.verb, e.path) for e in self.endpoints]


def _statuses(value: object) -> list[int | str]:
    """A declared status list: numbers stay numbers, range text stays text."""
    if not isinstance(value, (list, tuple)):
        return []
    out: list[int | str] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, str)):
            continue
        out.append(item if isinstance(item, str) else int(item))
    return out


def _as_endpoint(value: object) -> Endpoint | None:
    if isinstance(value, Endpoint):
        return value
    if isinstance(value, str):
        method, _, path = value.partition(" ")
        return Endpoint(method, path or "/")
    if isinstance(value, dict):
        return Endpoint(
            method=str(value.get("method", "GET")),
            path=str(value.get("path", "/")),
            auth=bool(value.get("auth", True)),
            statuses=_statuses(value.get("statuses", [])),
            deprecated=bool(value.get("deprecated", False)),
        )
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return Endpoint(str(value[0]), str(value[1]))
    return None


def _as_api(value: object) -> API | None:
    if isinstance(value, API):
        value.endpoints = convert_items(value.endpoints, _as_endpoint, field="endpoints")
        return value
    if isinstance(value, dict) and "endpoints" in value:
        return API(
            endpoints=convert_items(value["endpoints"], _as_endpoint, field="endpoints"),
            base=str(value.get("base", "/v1")),
            name=str(value.get("name", "api")),
            auth_schemes=convert_names(value.get("auth_schemes", []), field="auth_schemes"),
        )
    if isinstance(value, (list, tuple)):
        return API(endpoints=convert_items(value, _as_endpoint, field="endpoints"))
    return None


def load_api(path: str | Path) -> tuple[API, object]:
    # An OpenAPI document is the contract most projects already have; a `.json`
    # path is read as one rather than executed as Python.
    if Path(path).suffix.lower() == ".json":
        from .openapi import api_from_file

        return api_from_file(path), path

    from gxcore.loading import load_from_file

    api, module = load_from_file(
        path,
        attrs=("api", "API", "contract", "ENDPOINTS", "endpoints"),
        builders=("build", "make_api", "make"),
        convert=_as_api,
        description="api (an API)",
    )
    api.name = getattr(module, "NAME", Path(path).stem)
    return api, module


def api_from_parts(
    endpoints: list[Endpoint] | None = None,
    base: str = "/v1",
    name: str = "api",
    auth_schemes: list[str] | None = None,
) -> API:
    return API(
        endpoints=list(endpoints or []),
        base=base,
        name=name,
        auth_schemes=convert_names(auth_schemes or [], field="auth_schemes"),
    )
