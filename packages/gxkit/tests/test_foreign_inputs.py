"""Point the inspector at a document the project already has.

An importer converts a foreign document into the tool's own model, so the same
codes apply to a published spec as to a hand-written declaration. Nothing here
loosens a check: a malformed document is an input failure, not an empty API.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

DOCUMENT = {
    "openapi": "3.0.3",
    "info": {"title": "Payments", "version": "1.4.0"},
    "servers": [{"url": "https://api.example.com/v1"}],
    "security": [{"bearer": []}],
    "components": {"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}},
    "paths": {
        "/v1/invoices": {
            "get": {"security": [{"bearer": []}], "responses": {"200": {}, "404": {}}},
            "post": {"security": [], "responses": {"201": {}}, "deprecated": True},
        },
        "/internal/refund": {"post": {"responses": {"200": {}}}},
    },
}


def _inspect(path, *flags, tool=None):
    argv = [
        "inspect",
        *([tool] if tool else []),
        str(path),
        "--json",
        "--no-storyboard",
        "--no-config",
    ]
    return subprocess.run(
        [sys.executable, "-c", "from gxkit.cli import main; raise SystemExit(main())", *argv],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def _codes(report):
    return [problem["code"] for problem in report["problems"]]


def test_a_published_spec_is_inspected_by_the_same_codes(tmp_path):
    document = tmp_path / "openapi.json"
    document.write_text(json.dumps(DOCUMENT), encoding="utf-8")
    result = _inspect(document, tool="apigx")
    assert result.returncode == 1, result.stderr
    report = json.loads(result.stdout)
    assert report["name"] == "Payments"
    assert set(_codes(report)) == {
        "unauthenticated-mutation",
        "unversioned-path",
        "no-error-status",
        "deprecated-endpoint",
    }
    assert report["errors"] == 1


def test_a_spec_that_inherits_its_security_has_no_unauthenticated_mutation(tmp_path):
    clean = json.loads(json.dumps(DOCUMENT))
    clean["paths"]["/v1/invoices"]["post"].pop("security")
    clean["paths"].pop("/internal/refund")
    clean["paths"]["/v1/invoices"]["post"]["responses"] = {"201": {}, "400": {}}
    clean["paths"]["/v1/invoices"]["post"].pop("deprecated")
    document = tmp_path / "openapi.json"
    document.write_text(json.dumps(clean), encoding="utf-8")
    result = _inspect(document, tool="apigx")
    assert result.returncode == 0, result.stdout
    assert _codes(json.loads(result.stdout)) == []


def test_a_declaration_still_inspects_after_the_importer(tmp_path):
    artifact = tmp_path / "api.py"
    artifact.write_text(
        'ENDPOINTS = [{"method": "GET", "path": "/v1/users"},'
        ' {"method": "POST", "path": "/v1/users", "auth": False}]\n',
        encoding="utf-8",
    )
    result = _inspect(artifact, tool="apigx")
    assert result.returncode == 1, result.stderr
    assert "unauthenticated-mutation" in _codes(json.loads(result.stdout))


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("{ not json", "not JSON"),
        ('{"openapi": "3.0.0"}', "no 'paths' object"),
        ('{"swagger": "2.0", "paths": {}}', "unsupported OpenAPI version"),
        ('{"openapi": "3.0.0", "paths": 42}', "no 'paths' object"),
        ('{"openapi": "3.0.0", "paths": {"/a": 42}}', "paths['/a'] is not an object"),
        ('{"openapi": "3.0.0", "paths": {"/a": {"get": 42}}}', "paths['/a'].get is not an object"),
        ("[]", "expected a JSON object"),
    ],
)
def test_a_malformed_document_is_an_input_failure_with_its_location(tmp_path, content, expected):
    document = tmp_path / "openapi.json"
    document.write_text(content, encoding="utf-8")
    result = _inspect(document, tool="apigx")
    assert result.returncode == 2, result.stdout
    assert expected in result.stderr and "Traceback" not in result.stderr


def test_a_document_needs_the_tool_named(tmp_path):
    """Auto-detection reads a Python module; a foreign document says so."""
    document = tmp_path / "openapi.json"
    document.write_text(json.dumps(DOCUMENT), encoding="utf-8")
    result = _inspect(document)
    assert result.returncode == 2
    assert "apigx" in result.stderr and "Traceback" not in result.stderr
    assert "SyntaxError" not in result.stderr
