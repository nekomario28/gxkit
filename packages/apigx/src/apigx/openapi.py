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

# Everything a path item or an operation may say. A key outside these is refused
# rather than ignored: a mistyped `securty` would otherwise read as inherited
# security and hide a public mutation, and a mistyped method would drop a route
# without a word. Vendor extensions (`x-…`) are the spec's own escape hatch.
PATH_ITEM_KEYS = frozenset(METHODS) | {"$ref", "summary", "description", "servers", "parameters"}
#: What the reader accounts for at each level. A key it does not read is refused
#: wherever it appears — `info` and `components` were read with `.get()` and never
#: checked, so a document with a misspelled `titl` or an unknown root key reported
#: clean, which is the silence this family refuses. Keys it *knows but does not
#: need* (tags, externalDocs, schemas) are listed: accounting for something is not
#: the same as reading it.
ROOT_KEYS = frozenset(
    {
        "openapi",
        "info",
        "jsonSchemaDialect",
        "servers",
        "paths",
        "webhooks",
        "components",
        "security",
        "tags",
        "externalDocs",
    }
)
INFO_KEYS = frozenset(
    {
        "title",
        "summary",
        "description",
        "termsOfService",
        "contact",
        "license",
        "version",
    }
)
COMPONENTS_KEYS = frozenset(
    {
        "schemas",
        "responses",
        "parameters",
        "examples",
        "requestBodies",
        "headers",
        "securitySchemes",
        "links",
        "callbacks",
        "pathItems",
    }
)
OPERATION_KEYS = frozenset(
    {
        # `$ref` is legitimate and has its own refusal, below — refusing it as an
        # unknown key would say less than why it is refused.
        "$ref",
        "tags",
        "summary",
        "description",
        "externalDocs",
        "operationId",
        "parameters",
        "requestBody",
        "responses",
        "callbacks",
        "deprecated",
        "security",
        "servers",
    }
)


def _unrecognised(keys: dict[str, Any], known: frozenset[str]) -> list[str]:
    return sorted(
        str(key) for key in keys if str(key) not in known and not str(key).lower().startswith("x-")
    )


def _security_of(operation: dict[str, Any], document: dict[str, Any]) -> bool:
    """An operation is authenticated when no alternative permits anonymous access.

    A missing `security` inherits the document's; an empty list means the
    operation deliberately requires none. Alternatives are ORed, and an empty
    requirement object (`security: [{}]`) is an alternative that requires
    nothing — so it makes the operation anonymous however many schemes are
    listed beside it. Reading it as authenticated would hide a public mutation.
    """
    for where, holder in (("operation", operation), ("document", document)):
        if "security" in holder and not isinstance(holder["security"], list):
            # An object here is a malformed document (`security` is an array of
            # requirement objects). Reading it as "anonymous" turned a typo into a
            # hard "this mutation is public" error — a verdict on a document that
            # does not say that.
            raise InvalidArtifact(
                f"security must be an array of requirement objects, and the {where} "
                f"has {type(holder['security']).__name__}"
            )
    requirements = operation["security"] if "security" in operation else document.get("security")
    if not isinstance(requirements, list) or not requirements:
        return False
    for requirement in requirements:
        if not isinstance(requirement, dict):
            raise InvalidArtifact(
                f"a security requirement must be an object, not {type(requirement).__name__}"
            )
    return all(requirement for requirement in requirements)


#: The ranged response keys OpenAPI defines, plus `default`.
_RANGES = frozenset({"1XX", "2XX", "3XX", "4XX", "5XX"})


def _statuses(responses: object) -> list[int | str]:
    """The declared statuses: numbers, plus the ranged keys as written.

    `5XX` and `default` are legal and meaningful, and dropping them made
    `no-error-status` fire on an operation that documents its errors (measured).
    They are kept as text because a range is not a number.
    """
    if not isinstance(responses, dict):
        return []
    codes: list[int | str] = []
    for key in responses:
        if isinstance(key, str) and key.upper() in _RANGES:
            codes.append(key.upper())
            continue
        if isinstance(key, str) and key.lower() == "default":
            codes.append("default")
            continue
        if isinstance(key, str) and key.isdigit():
            try:
                codes.append(int(key))
            except ValueError as exc:
                # `isdigit` is true for characters `int` rejects — a superscript
                # '²' among them — so this branch is reachable and is tested.
                raise InvalidArtifact(f"responses: {key!r} is not a status code") from exc
    # Ints and the range strings do not compare: sort by their text form, which is
    # a total order and keeps `1XX` before `200` before `default`.
    return sorted(codes, key=str)


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


def _base(document: dict[str, Any]) -> str:
    """The base the document declares, and nothing else.

    A prefix inferred from the paths would look like a check had been applied
    while being unable to fail: every path shares a prefix by construction, so
    `path-outside-base` can only fire on a declaration. Reporting no base when the
    document declares none is the honest reading.
    """
    return _server_path(document)


def _override_path(servers: object) -> str | None:
    """The path an operation- or path-item-level `servers` overrides with."""
    if not isinstance(servers, list) or not servers or not isinstance(servers[0], dict):
        return None
    return urlparse(str(servers[0].get("url", ""))).path.rstrip("/")


def _reference_in(value: object, where: str = "") -> str | None:
    """The location of the first `$ref` in a parsed document, or None.

        This importer resolves no reference, so a document that has one anywhere is a
    document it did not read through. Only the path-item and operation cases were
        checked, so a `$ref` in `parameters`, `requestBody` or a response schema was
        accepted and the document read as complete (measured).
    """
    if isinstance(value, dict):
        if "$ref" in value:
            return f"{where}.$ref" if where else "$ref"
        for key, item in value.items():
            found = _reference_in(item, f"{where}.{key}" if where else str(key))
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found = _reference_in(item, f"{where}[{index}]")
            if found is not None:
                return found
    return None


def api_from_document(document: object, *, source: str = "openapi") -> API:
    """An `API` from a parsed OpenAPI 3 document, or a located rejection."""
    if not isinstance(document, dict):
        raise InvalidArtifact(f"{source}: expected a JSON object")
    version = document.get("openapi")
    if not isinstance(version, str) or not version.startswith("3."):
        raise InvalidArtifact(f"{source}: unsupported OpenAPI version {version!r} (3.x only)")
    unknown = _unrecognised(document, ROOT_KEYS)
    if unknown:
        raise InvalidArtifact(
            f"{source}: unrecognised root key(s) {unknown}; refusing rather than "
            "ignoring them, because a key nothing reads is a document that is not "
            "fully read"
        )
    for section, known in (("info", INFO_KEYS), ("components", COMPONENTS_KEYS)):
        value = document.get(section)
        if value is None:
            continue
        if not isinstance(value, dict):
            raise InvalidArtifact(f"{source}: {section} is not an object")
        unknown = _unrecognised(value, known)
        if unknown:
            raise InvalidArtifact(f"{source}: {section} has unrecognised key(s) {unknown}")
    paths = document.get("paths")
    if not isinstance(paths, dict):
        raise InvalidArtifact(f"{source}: no 'paths' object")
    for path in paths:
        if not str(path).startswith("/") and not str(path).lower().startswith("x-"):
            raise InvalidArtifact(
                f"{source}: paths has key {path!r}, which is not a path (it must begin "
                "with '/'); a mistyped path would otherwise be read as one"
            )
    if document.get("webhooks"):
        raise InvalidArtifact(
            f"{source}: 'webhooks' declares operations this importer does not read; "
            "refusing rather than reporting a partial API"
        )
    reference = _reference_in(document, "")
    if reference is not None:
        raise InvalidArtifact(
            f"{source}: {reference} is a reference; this importer does not resolve "
            "references, and a document with one is not fully read"
        )
    schemes = document.get("components", {})
    auth_schemes = (
        sorted(str(name) for name in schemes["securitySchemes"])
        if isinstance(schemes, dict) and isinstance(schemes.get("securitySchemes"), dict)
        else []
    )
    server_path = _server_path(document)
    endpoints: list[Endpoint] = []
    for path, operations in paths.items():
        # A specification extension holds arbitrary data, not a path item: iterating
        # one as a path invented an endpoint (measured: `x-internal` holding a `get`
        # became `GET /v1/x-internal`), and a scalar one was refused as "not an
        # object". The key-shape guard above already allows `x-`; this is where the
        # allowance has to land.
        if str(path).lower().startswith("x-"):
            continue
        if not isinstance(operations, dict):
            raise InvalidArtifact(f"{source}: paths[{path!r}] is not an object")
        # OpenAPI lets a path item or an operation override the server, and the
        # model carries one base for the whole API. Overriding *the path* would
        # make the endpoint something other than what this reports, so it is
        # refused; a host-only override does not change the path and is fine.
        path_override = _override_path(operations.get("servers"))
        if path_override is not None and path_override != server_path:
            raise InvalidArtifact(
                f"{source}: paths[{path!r}] overrides the server path "
                f"({path_override!r} vs {server_path!r}), which this importer cannot "
                "represent; declare the API in Python"
            )
        unknown = _unrecognised(operations, PATH_ITEM_KEYS)
        if unknown:
            raise InvalidArtifact(
                f"{source}: paths[{path!r}] has unrecognised key(s) {unknown}; refusing "
                "rather than ignoring them, because a mistyped key changes the verdict"
            )
        for method in METHODS:
            operation = operations.get(method)
            if operation is None:
                continue
            if not isinstance(operation, dict):
                raise InvalidArtifact(f"{source}: paths[{path!r}].{method} is not an object")
            unknown = _unrecognised(operation, OPERATION_KEYS)
            if unknown:
                raise InvalidArtifact(
                    f"{source}: paths[{path!r}].{method} has unrecognised key(s) {unknown}; "
                    "refusing rather than ignoring them"
                )
            if "responses" not in operation:
                # `responses` is REQUIRED by OpenAPI, and an operation without one
                # has an undefined status set — reading it as a valid API turned a
                # required-field violation into an info about a missing error status.
                raise InvalidArtifact(
                    f"{source}: paths[{path!r}].{method} declares no 'responses'; "
                    "OpenAPI requires them, and without them the status set is undefined"
                )
            if "deprecated" in operation and not isinstance(operation["deprecated"], bool):
                # `bool("false")` is True: a string typo would be silently read as
                # "deprecated", which the document does not say.
                raise InvalidArtifact(
                    f"{source}: paths[{path!r}].{method}.deprecated is "
                    f"{type(operation['deprecated']).__name__}, not a boolean"
                )
            operation_override = _override_path(operation.get("servers"))
            if operation_override is not None and operation_override != server_path:
                raise InvalidArtifact(
                    f"{source}: paths[{path!r}].{method} overrides the server path "
                    f"({operation_override!r} vs {server_path!r}), which this importer cannot "
                    "represent; declare the API in Python"
                )
            statuses = _statuses(operation.get("responses"))
            responses = operation.get("responses")
            if not isinstance(responses, dict):
                raise InvalidArtifact(
                    f"{source}: paths[{path!r}].{method}.responses is "
                    f"{type(responses).__name__}, not an object"
                )
            # A response entry is an object (or a reference, already refused). A
            # string there was accepted and the status read as if the document had
            # said what that status carries.
            for key, value in responses.items():
                if not isinstance(value, dict):
                    raise InvalidArtifact(
                        f"{source}: paths[{path!r}].{method}.responses[{key!r}] is "
                        f"{type(value).__name__}, not an object"
                    )
            endpoints.append(
                Endpoint(
                    method.upper(),
                    _endpoint_path(server_path, str(path)),
                    auth=_security_of(operation, document),
                    statuses=statuses,
                    deprecated=bool(operation.get("deprecated", False)),
                )
            )
    info = document.get("info")
    name = str(info["title"]) if isinstance(info, dict) and info.get("title") else "api"
    return API(
        endpoints=endpoints,
        base=_base(document),
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
