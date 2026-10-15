"""The OpenAPI importer: every branch, because coverage is the floor here."""

from __future__ import annotations

import json

import pytest
from apigx import API, Endpoint, api_from_document, api_from_file, inspect_api, load_api
from gxcore.loading import InvalidArtifact

BASE = {
    "openapi": "3.0.3",
    "info": {"title": "Payments"},
    "servers": [{"url": "https://api.example.com/v1"}],
    "security": [{"bearer": []}],
    "components": {"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}},
    "paths": {"/invoices": {"get": {"responses": {"200": {}, "404": {}}}}},
}


def _doc(**changes):
    document = json.loads(json.dumps(BASE))
    document.update(changes)
    return document


def test_a_document_becomes_endpoints_with_their_authentication():
    api = api_from_document(_doc())
    assert api.name == "Payments"
    assert api.base == "/v1"
    assert api.endpoints == [Endpoint("GET", "/v1/invoices", auth=True, statuses=[200, 404])]


@pytest.mark.parametrize(
    ("operation", "auth"),
    [
        ({"security": [{"bearer": []}], "responses": {}}, True),
        ({"security": [], "responses": {}}, False),
        ({"responses": {}}, True),
    ],
)
def test_authentication_is_inherited_unless_the_operation_says_otherwise(operation, auth):
    api = api_from_document(_doc(paths={"/a": {"post": operation}}))
    assert [endpoint.auth for endpoint in api.endpoints] == [auth]


def test_a_document_without_security_has_an_unauthenticated_api():
    document = _doc(paths={"/a": {"post": {"responses": {}}}})
    document.pop("security")
    assert [endpoint.auth for endpoint in api_from_document(document).endpoints] == [False]


def test_statuses_come_from_the_numeric_response_keys():
    api = api_from_document(
        _doc(paths={"/a": {"get": {"responses": {"404": {}, "default": {}, "201": {}}}}})
    )
    assert api.endpoints[0].statuses == [201, 404]


@pytest.mark.parametrize("responses", [None, 42, [], "x"])
def test_responses_that_are_not_an_object_document_no_status(responses):
    api = api_from_document(_doc(paths={"/a": {"get": {"responses": responses}}}))
    assert api.endpoints[0].statuses == []


def test_a_status_key_that_looks_numeric_but_is_not_is_rejected():
    with pytest.raises(InvalidArtifact, match="responses"):
        api_from_document(_doc(paths={"/a": {"get": {"responses": {"²": {}}}}}))


def test_deprecated_survives_the_conversion():
    api = api_from_document(_doc(paths={"/a": {"get": {"responses": {}, "deprecated": True}}}))
    assert api.endpoints[0].deprecated is True


@pytest.mark.parametrize("method", ["get", "put", "post", "delete", "patch", "head", "options"])
def test_every_http_method_becomes_an_endpoint(method):
    api = api_from_document(_doc(paths={"/a": {method: {"responses": {}}}}))
    assert [endpoint.verb for endpoint in api.endpoints] == [method.upper()]


def test_an_unknown_key_in_a_path_item_is_not_an_endpoint():
    api = api_from_document(_doc(paths={"/a": {"parameters": [], "trace": {"responses": {}}}}))
    assert [endpoint.verb for endpoint in api.endpoints] == ["TRACE"]


@pytest.mark.parametrize(
    ("servers", "paths", "expected"),
    [
        ([{"url": "https://api.example.com/v1/"}], ["/a"], "/v1"),
        ([{"url": "https://api.example.com"}], ["/a"], ""),
        # No declared server means no declared base: a prefix inferred from the
        # paths could never fail a check, so it is not reported as one.
        ([], ["/v1/a", "/v1/b"], ""),
        ([], ["/a"], ""),
        ([{"url": "https://api.example.com/v1", "x": 1}], ["/a"], "/v1"),
    ],
)
def test_the_base_comes_from_the_server_and_not_from_an_inferred_prefix(servers, paths, expected):
    document = _doc(servers=servers, paths={path: {"get": {"responses": {}}} for path in paths})
    assert api_from_document(document).base == expected


def test_an_operation_path_is_relative_to_the_server_path():
    """OpenAPI defines the endpoint as the server's path followed by the path."""
    api = api_from_document(_doc(paths={"/items": {"post": {"responses": {}}}}))
    assert [endpoint.path for endpoint in api.endpoints] == ["/v1/items"]
    assert "unversioned-path" not in {problem.code for problem in inspect_api(api).problems}


def test_a_server_without_a_path_does_not_prefix_anything():
    document = _doc(servers=[{"url": "https://api.example.com"}], paths={"/items": {"get": {}}})
    api = api_from_document(document)
    assert api.base == "" and [endpoint.path for endpoint in api.endpoints] == ["/items"]


@pytest.mark.parametrize(
    "security",
    [
        [{}],
        [{}, {"bearer": []}],
        [{"bearer": []}, {}],
    ],
)
def test_an_anonymous_alternative_makes_the_operation_public(security):
    """Alternatives are ORed, so one that requires nothing permits anyone."""
    document = _doc(paths={"/a": {"post": {"security": security, "responses": {}}}})
    api = api_from_document(document)
    assert [endpoint.auth for endpoint in api.endpoints] == [False]
    assert "unauthenticated-mutation" in {problem.code for problem in inspect_api(api).problems}


def test_an_anonymous_alternative_inherited_from_the_document_is_public_too():
    document = _doc(paths={"/a": {"post": {"responses": {}}}})
    document["security"] = [{}, {"bearer": []}]
    assert [endpoint.auth for endpoint in api_from_document(document).endpoints] == [False]


@pytest.mark.parametrize(
    "path_item",
    [
        {"$ref": "#/components/pathItems/Invoices"},
        {"post": {"$ref": "#/components/operations/charge"}},
    ],
)
def test_a_reference_is_refused_rather_than_dropped(path_item):
    with pytest.raises(InvalidArtifact, match="reference"):
        api_from_document(_doc(paths={"/items": path_item}))


@pytest.mark.parametrize(
    ("path_item", "expected"),
    [
        # A mistyped method would drop the route; ignoring it would report an API
        # that does not contain what the document declares.
        ({"psot": {"responses": {}}}, "unrecognised key"),
        # A mistyped `security` would read as inherited authentication.
        ({"post": {"securty": [], "responses": {}}}, "unrecognised key"),
    ],
)
def test_an_unrecognised_key_is_refused_rather_than_ignored(path_item, expected):
    with pytest.raises(InvalidArtifact, match=expected):
        api_from_document(_doc(paths={"/items": path_item}))


def test_a_vendor_extension_is_allowed_because_the_spec_allows_it():
    api = api_from_document(_doc(paths={"/items": {"get": {"responses": {}, "x-internal": True}}}))
    assert [endpoint.verb for endpoint in api.endpoints] == ["GET"]


def test_operations_outside_paths_are_refused_rather_than_skipped():
    """`webhooks` holds operations too; reading paths only would be partial."""
    document = _doc()
    document["webhooks"] = {"ping": {"post": {"responses": {}}}}
    with pytest.raises(InvalidArtifact, match="webhooks"):
        api_from_document(document)


def test_the_whole_operation_vocabulary_is_accepted():
    operation = {
        "tags": ["a"],
        "summary": "s",
        "description": "d",
        "externalDocs": {"url": "https://example.com"},
        "operationId": "op",
        "parameters": [],
        "requestBody": {},
        "responses": {"200": {}},
        "callbacks": {},
        "deprecated": False,
        "security": [{"bearer": []}],
        "servers": [],
    }
    api = api_from_document(_doc(paths={"/a": {"post": operation}}))
    assert [endpoint.verb for endpoint in api.endpoints] == ["POST"]


@pytest.mark.parametrize(
    ("server", "expected"),
    [
        ({"url": "https://api.example.com/v1"}, "/v1"),
        ({"url": "https://api.example.com"}, ""),
        ({"url": "https://api.example.com/v1/"}, "/v1"),
    ],
)
def test_an_override_is_read_for_the_path_it_declares(server, expected):
    from apigx.openapi import _override_path

    assert _override_path([server]) == expected


@pytest.mark.parametrize("servers", [None, [], "https://example.com", [42], [{}]])
def test_an_override_with_no_usable_server_is_not_a_server(servers):
    from apigx.openapi import _override_path

    assert _override_path(servers) in {None, ""}


def test_a_path_item_override_that_changes_the_path_is_refused():
    with pytest.raises(InvalidArtifact, match="overrides the server path"):
        api_from_document(
            _doc(
                servers=[{"url": "https://api.example.com/v1"}],
                paths={
                    "/items": {"servers": [{"url": "https://api.example.com/legacy"}], "get": {}}
                },
            )
        )


def test_an_operation_override_that_changes_the_path_is_refused():
    with pytest.raises(InvalidArtifact, match="overrides the server path"):
        api_from_document(
            _doc(
                servers=[{"url": "https://api.example.com/v1"}],
                paths={
                    "/items": {
                        "get": {
                            "responses": {},
                            "servers": [{"url": "https://api.example.com/legacy"}],
                        }
                    }
                },
            )
        )


def test_an_override_that_only_names_a_host_is_allowed():
    """A host-only override does not change the path, so the model still holds."""
    api = api_from_document(
        _doc(
            servers=[{"url": "https://api.example.com"}],
            paths={"/items": {"get": {"responses": {}, "servers": [{"url": "https://other"}]}}},
        )
    )
    assert [endpoint.path for endpoint in api.endpoints] == ["/items"]


def test_security_schemes_become_the_declared_scheme_names():
    api = api_from_document(_doc())
    assert api.auth_schemes == ["bearer"]


@pytest.mark.parametrize("components", [None, {}, {"securitySchemes": 42}, {"securitySchemes": {}}])
def test_missing_scheme_declarations_are_an_empty_list(components):
    document = _doc()
    if components is None:
        document.pop("components")
    else:
        document["components"] = components
    assert api_from_document(document).auth_schemes == []


def test_a_document_without_a_title_is_still_an_api():
    document = _doc()
    document.pop("info")
    assert api_from_document(document).name == "api"
    assert api_from_document(_doc(info={})).name == "api"


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        ([], "expected a JSON object"),
        ("x", "expected a JSON object"),
        ({"paths": {}}, "unsupported OpenAPI version"),
        ({"openapi": "2.0", "paths": {}}, "unsupported OpenAPI version"),
        ({"openapi": "3.0.0"}, "no 'paths' object"),
        ({"openapi": "3.0.0", "paths": 42}, "no 'paths' object"),
        ({"openapi": "3.0.0", "paths": {"/a": 42}}, "paths['/a'] is not an object"),
        ({"openapi": "3.0.0", "paths": {"/a": {"get": 42}}}, "paths['/a'].get is not an object"),
    ],
)
def test_a_document_that_is_not_openapi_3_is_rejected_where_it_is_wrong(document, expected):
    with pytest.raises(InvalidArtifact) as info:
        api_from_document(document, source="spec.json")
    assert expected in str(info.value) and "spec.json" in str(info.value)


def test_a_file_is_read_as_json(tmp_path):
    document = tmp_path / "openapi.json"
    document.write_text(json.dumps(BASE), encoding="utf-8")
    api, _module = load_api(document)
    assert api.name == "Payments"
    assert api_from_file(document).endpoints == api.endpoints


def test_a_file_that_is_not_json_names_itself(tmp_path):
    document = tmp_path / "openapi.json"
    document.write_text("{ not json", encoding="utf-8")
    with pytest.raises(InvalidArtifact, match="not JSON"):
        api_from_file(document)


def test_a_missing_document_is_an_input_failure(tmp_path):
    with pytest.raises(InvalidArtifact, match=r"openapi\.json"):
        api_from_file(tmp_path / "openapi.json")


def test_the_conversion_is_an_api_the_checks_accept():
    from apigx import inspect_api

    document = _doc(
        paths={
            "/v1/invoices": {"post": {"security": [], "responses": {"201": {}}, "deprecated": True}}
        }
    )
    report = inspect_api(api_from_document(document))
    assert {problem.code for problem in report.problems} == {
        "unauthenticated-mutation",
        "no-error-status",
        "deprecated-endpoint",
    }
    assert report.errors == 1


def test_a_python_declaration_is_still_the_other_route(tmp_path):
    artifact = tmp_path / "api.py"
    artifact.write_text('API = [{"method": "GET", "path": "/v1/users"}]\n', encoding="utf-8")
    api, _module = load_api(artifact)
    assert isinstance(api, API)
    assert api.endpoints[0].verb == "GET"
