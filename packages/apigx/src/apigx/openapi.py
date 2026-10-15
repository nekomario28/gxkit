"""Read the API contract a project already has: an OpenAPI 3 document.

A declaration is precise, but most services already publish a spec. Converting
one costs nothing and changes no claim: the converted document is inspected by
exactly the same checks as a hand-written declaration, so an unauthenticated
mutation in a published spec is the same defect as one in a declaration.

Only the standard library reads the document, so an importer adds no runtime
dependency. OpenAPI 2 / Swagger is not supported: its shape differs enough that
guessing would inspect the wrong thing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from gxcore.loading import InvalidArtifact

from .model import API, Endpoint

METHODS = ("get", "put", "post", "delete", "patch", "head", "options", "trace")


def _security_of(operation: dict[str, Any], document: dict[str, Any]) -> bool:
    """An operation is authenticated when no alternative permits anonymous access.

    A missing `security` inherits the document's; an empty list means the
    operation deliberately requires none. Alternatives are ORed, and an empty
    requirement object (`security: [{}]`) is an alternative that requires
    nothing — so it makes the operation anonymous however many schemes are
    listed beside it. Reading it as authenticated would hide a public mutation.
    """
    requirements = operation["security"] if "security" in operation else document.get("security")
    if not isinstance(requirements, list) or not requirements:
        return False
    return all(isinstance(requirement, dict) and requirement for requirement in requirements)


def _statuses(responses: object) -> list[int]:
    if not isinstance(responses, dict):
        return []
    codes = []
    for key in responses:
        if isinstance(key, str) and key.isdigit():
            try:
                codes.append(int(key))
            except ValueError as exc:  # pragma: no cover - isdigit already guarantees this
                raise InvalidArtifact(f"responses: {key!r} is not a status code") from exc
    return sorted(codes)


def _server_path(document: dict[str, Any]) -> str:
    """The path prefix every operation path is relative to, if the document says.

    OpenAPI defines an endpoint as the server's URL path followed by the path
    item, so `/items` under `servers: [{"url": "https://api.example.com/v1"}]` is
    `/v1/items`. Comparing the unprefixed form against the base would report a
    correctly versioned endpoint as unversioned.
    """
    servers = document.get("servers")
    if isinstance(servers, list) and servers and isinstance(servers[0], dict):
        return urlparse(str(servers[0].get("url", ""))).path.rstrip("/")
    return ""


def _endpoint_path(server_path: str, path: str) -> str:
    if not server_path:
        return path
    return server_path + (path if path.startswith("/") else f"/{path}")


def _base(document: dict[str, Any], paths: list[str]) -> str:
    """The versioned base: the server's path, or the paths' shared prefix."""
    server_path = _server_path(document)
    if server_path:
        return server_path
    if len(paths) > 1:
        prefix = paths[0]
        for path in paths[1:]:
            while not path.startswith(prefix):
                prefix = prefix[: prefix.rfind("/")]
                if not prefix:
                    return ""
        return prefix.rstrip("/")
    return ""


def api_from_document(document: object, *, source: str = "openapi") -> API:
    """An `API` from a parsed OpenAPI 3 document, or a located rejection."""
    if not isinstance(document, dict):
        raise InvalidArtifact(f"{source}: expected a JSON object")
    version = document.get("openapi")
    if not isinstance(version, str) or not version.startswith("3."):
        raise InvalidArtifact(f"{source}: unsupported OpenAPI version {version!r} (3.x only)")
    paths = document.get("paths")
    if not isinstance(paths, dict):
        raise InvalidArtifact(f"{source}: no 'paths' object")
    schemes = document.get("components", {})
    auth_schemes = (
        sorted(str(name) for name in schemes["securitySchemes"])
        if isinstance(schemes, dict) and isinstance(schemes.get("securitySchemes"), dict)
        else []
    )
    server_path = _server_path(document)
    endpoints: list[Endpoint] = []
    for path, operations in paths.items():
        if not isinstance(operations, dict):
            raise InvalidArtifact(f"{source}: paths[{path!r}] is not an object")
        if "$ref" in operations:
            raise InvalidArtifact(
                f"{source}: paths[{path!r}] is a reference; this importer does not resolve "
                "references, and skipping it would drop the route without saying so"
            )
        for method in METHODS:
            operation = operations.get(method)
            if operation is None:
                continue
            if not isinstance(operation, dict):
                raise InvalidArtifact(f"{source}: paths[{path!r}].{method} is not an object")
            if "$ref" in operation:
                raise InvalidArtifact(
                    f"{source}: paths[{path!r}].{method} is a reference; this importer does not "
                    "resolve references"
                )
            endpoints.append(
                Endpoint(
                    method.upper(),
                    _endpoint_path(server_path, str(path)),
                    auth=_security_of(operation, document),
                    statuses=_statuses(operation.get("responses")),
                    deprecated=bool(operation.get("deprecated", False)),
                )
            )
    info = document.get("info")
    name = str(info["title"]) if isinstance(info, dict) and info.get("title") else "api"
    return API(
        endpoints=endpoints,
        base=_base(document, [endpoint.path for endpoint in endpoints]),
        name=name,
        auth_schemes=auth_schemes,
    )


def api_from_file(path: str | Path) -> API:
    """An `API` from an OpenAPI 3 JSON document on disk."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InvalidArtifact(f"{path}: {exc}") from exc
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidArtifact(f"{path}: not JSON ({exc})") from exc
    return api_from_document(document, source=str(path))
