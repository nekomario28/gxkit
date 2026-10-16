"""Prove every apigx check fires on an API that has the fault and stays quiet otherwise."""

from __future__ import annotations

from pathlib import Path

import pytest
from apigx import API, Endpoint, api_from_parts, inspect_api, load_api
from gxcore import ERROR, INFO, WARN
from gxcore.loading import InvalidArtifact
from gxcore.testing import assert_fires, assert_quiet


def test_a_clean_api_has_no_problems():
    api = API(base="/v1", endpoints=[Endpoint("GET", "/v1/users", statuses=[200, 404])])
    assert inspect_api(api).problems == []


def test_duplicate_route():
    api = API(
        base="/v1",
        endpoints=[
            Endpoint("GET", "/v1/x", statuses=[200]),
            Endpoint("GET", "/v1/x", statuses=[200]),
        ],
    )
    assert_fires(inspect_api(api), "duplicate-route", ERROR)


def test_unauthenticated_mutation():
    api = API(base="/v1", endpoints=[Endpoint("POST", "/v1/x", auth=False, statuses=[201])])
    assert_fires(inspect_api(api), "unauthenticated-mutation", ERROR)


def test_a_read_without_auth_is_fine():
    api = API(base="/v1", endpoints=[Endpoint("GET", "/v1/x", auth=False, statuses=[200])])
    assert_quiet(inspect_api(api), "unauthenticated-mutation")


def test_unversioned_path():
    api = API(base="/v1", endpoints=[Endpoint("GET", "/users", statuses=[200])])
    assert_fires(inspect_api(api), "path-outside-base", WARN)


def test_no_error_status():
    api = API(base="/v1", endpoints=[Endpoint("GET", "/v1/x", statuses=[200])])
    assert_fires(inspect_api(api), "no-error-status", INFO)


def test_deprecated_endpoint():
    api = API(base="/v1", endpoints=[Endpoint("GET", "/v1/x", statuses=[200], deprecated=True)])
    assert_fires(inspect_api(api), "deprecated-endpoint", INFO)


def test_no_endpoints():
    assert_fires(inspect_api(API()), "no-endpoints", INFO)


def test_api_from_parts_roundtrips():
    api = api_from_parts(endpoints=[Endpoint("GET", "/v1/x")], base="/v1", name="x")
    assert api.routes() == [("GET", "/v1/x")]
    assert api.name == "x"


def test_loader_accepts_a_list_of_strings(tmp_path):
    src = tmp_path / "a.py"
    src.write_text('ENDPOINTS = ["GET /v1/a", "POST /v1/b"]\nNAME = "x"\n')
    api, _module = load_api(src)
    assert [e.label() for e in api.endpoints] == ["GET /v1/a", "POST /v1/b"]
    assert api.name == "x"


def test_loader_accepts_a_dict(tmp_path):
    src = tmp_path / "a.py"
    src.write_text(
        'API = {"base": "/v2", "endpoints": ['
        '{"method": "GET", "path": "/v2/x", "statuses": [200]}]}\n'
    )
    api, _module = load_api(src)
    assert api.base == "/v2"
    assert api.endpoints[0].path == "/v2/x"


def test_examples_load_and_are_diagnosed():
    examples = Path(__file__).resolve().parents[1] / "examples"
    good, _ = load_api(examples / "good_api.py")
    broken, _ = load_api(examples / "broken_api.py")
    assert inspect_api(good).errors == 0
    report = inspect_api(broken)
    for code, severity in (
        ("duplicate-route", ERROR),
        ("unauthenticated-mutation", ERROR),
        ("path-outside-base", WARN),
        ("no-error-status", INFO),
        ("deprecated-endpoint", INFO),
    ):
        assert_fires(report, code, severity)


def test_endpoint_and_api_converters():
    from apigx.model import _as_api, _as_endpoint

    endpoint = Endpoint("GET", "/v1/x")
    assert _as_endpoint(endpoint) is endpoint
    assert _as_endpoint(("GET", "/v1/x")).path == "/v1/x"
    assert _as_endpoint(42) is None

    api = API()
    assert _as_api(api) is api
    assert _as_api([("GET", "/v1/x")]).routes() == [("GET", "/v1/x")]
    with pytest.raises(InvalidArtifact, match=r"endpoints\[0\]"):
        _as_api([42])
    assert _as_api(42) is None


def test_image_size_tracks_the_endpoint_count():
    from apigx.render import image_size

    assert image_size(API(base="/v1", endpoints=[Endpoint("GET", "/v1/x")]))[0] > 0
