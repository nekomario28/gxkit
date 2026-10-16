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
        "/invoices": {
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
    # An imported spec carries its base in `servers`, so every endpoint is under
    # it and `unversioned-path` cannot fire; the other three codes still do.
    assert set(_codes(report)) == {
        "unauthenticated-mutation",
        "no-error-status",
        "deprecated-endpoint",
    }
    assert report["errors"] == 1


def test_a_spec_that_inherits_its_security_has_no_unauthenticated_mutation(tmp_path):
    clean = json.loads(json.dumps(DOCUMENT))
    clean["paths"]["/invoices"]["post"].pop("security")
    clean["paths"].pop("/internal/refund")
    clean["paths"]["/invoices"]["post"]["responses"] = {"201": {}, "400": {}}
    clean["paths"]["/invoices"]["post"].pop("deprecated")
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


SQL = """
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL
);

CREATE TABLE posts (
    id BIGSERIAL PRIMARY KEY,
    author_id INTEGER,
    FOREIGN KEY (author_id) REFERENCES users (email)
);
"""


def test_a_sql_file_is_inspected_by_the_same_codes(tmp_path):
    document = tmp_path / "schema.sql"
    document.write_text(SQL, encoding="utf-8")
    result = _inspect(document, tool="schemagx")
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    # `not-modelled` joined the report when clauses the model cannot carry stopped
    # being dropped in silence (`NOT NULL`, `DEFAULT`, `UNIQUE`, …), which this
    # fixture has; the reference findings are unchanged.
    assert set(_codes(report)) == {"fk-type-mismatch", "fk-to-non-primary-key", "not-modelled"}


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("SELECT 1;\n", "not a CREATE TABLE statement"),
        ("CREATE TABLE a (id INT, PRIMARY KEY (id, x));\n", "composite primary key"),
        ("CREATE TABLE a (id INT) trailing;\n", "expected ';' after the table body"),
    ],
)
def test_a_sql_file_that_cannot_be_read_says_where_it_is_wrong(tmp_path, content, expected):
    document = tmp_path / "schema.sql"
    document.write_text(content, encoding="utf-8")
    result = _inspect(document, tool="schemagx")
    assert result.returncode == 2, result.stdout
    assert expected in result.stderr and "Traceback" not in result.stderr


def test_a_sql_document_needs_the_tool_named(tmp_path):
    document = tmp_path / "schema.sql"
    document.write_text(SQL, encoding="utf-8")
    result = _inspect(document)
    assert result.returncode == 2
    assert "not a Python artifact" in result.stderr


MERMAID = """stateDiagram-v2
    [*] --> cart
    cart --> paid : pay
    paid --> [*]
    abandoned --> cart : resume
"""


def test_a_mermaid_diagram_is_inspected_by_the_same_codes(tmp_path):
    document = tmp_path / "checkout.mmd"
    document.write_text(MERMAID, encoding="utf-8")
    result = _inspect(document, tool="flowgx")
    assert result.returncode == 1, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert _codes(report) == ["unreachable-state"]
    assert report["errors"] == 1


def test_a_diagram_drawn_in_a_document_is_read_through_it(tmp_path):
    document = tmp_path / "README.md"
    document.write_text(f"# Checkout\n\n```mermaid\n{MERMAID}```\n", encoding="utf-8")
    result = _inspect(document, tool="flowgx")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "unreachable-state" in _codes(json.loads(result.stdout))


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("stateDiagram-v2\n    [*] --> a\n    [*] --> b\n", "a second initial state"),
        ("flowchart LR\n    a --> b\n", "expected a `stateDiagram-v2` header"),
        (
            "stateDiagram-v2\n    state outer {\n        [*] --> inner\n    }\n",
            "a composite state is not representable",
        ),
    ],
)
def test_a_diagram_that_cannot_be_read_says_where_it_is_wrong(tmp_path, content, expected):
    document = tmp_path / "diagram.mmd"
    document.write_text(content, encoding="utf-8")
    result = _inspect(document, tool="flowgx")
    assert result.returncode == 2, result.stdout
    assert expected in result.stderr and "Traceback" not in result.stderr


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (
            "CREATE TABLE p (id INT PRIMARY KEY);\n"
            "CREATE TABLE c (a INT, b INT, FOREIGN KEY (a, b) REFERENCES p);\n",
            "composite foreign key",
        ),
    ],
)
def test_a_composite_key_is_still_refused_when_the_target_is_omitted(tmp_path, content, expected):
    """The child columns are checked before an omitted target is resolved.

    Returning early to resolve `REFERENCES p` used to keep the first column and
    drop the second, which is a silent narrowing of the statement.
    """
    document = tmp_path / "schema.sql"
    document.write_text(content, encoding="utf-8")
    result = _inspect(document, tool="schemagx")
    assert result.returncode == 2, result.stdout
    assert expected in result.stderr


def test_a_sql_literal_containing_a_comment_marker_is_read(tmp_path):
    """`DEFAULT '--'` is a value, not the start of a comment."""
    document = tmp_path / "schema.sql"
    document.write_text(
        "CREATE TABLE t (id INT PRIMARY KEY, label TEXT DEFAULT '--', note TEXT);\n",
        encoding="utf-8",
    )
    result = _inspect(document, "--json", tool="schemagx")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["errors"] == 0


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("CREATE TABLE t (id INT); /* unterminated\n", "unterminated"),
        ("CREATE TABLE t (id INT, x TEXT DEFAULT 'oops);\n", "unterminated"),
    ],
)
def test_an_unterminated_comment_or_literal_is_refused(tmp_path, content, expected):
    document = tmp_path / "schema.sql"
    document.write_text(content, encoding="utf-8")
    result = _inspect(document, tool="schemagx")
    assert result.returncode == 2, result.stdout
    assert expected in result.stderr


@pytest.mark.parametrize(
    ("document", "level"),
    [
        (
            {
                "openapi": "3.0.3",
                "servers": [{"url": "https://api.example.com/v1"}],
                "paths": {
                    "/items": {
                        "get": {
                            "responses": {},
                            "servers": [{"url": "https://api.example.com/legacy"}],
                        }
                    }
                },
            },
            "paths['/items'].get",
        ),
        (
            {
                "openapi": "3.0.3",
                "servers": [{"url": "https://api.example.com/v1"}],
                "paths": {
                    "/items": {
                        "servers": [{"url": "https://api.example.com/legacy"}],
                        "get": {"responses": {}},
                    }
                },
            },
            "paths['/items']",
        ),
    ],
)
def test_a_server_override_the_model_cannot_represent_is_refused(tmp_path, document, level):
    """One base per API, so an override that changes the path is an input failure."""
    path = tmp_path / "openapi.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    result = _inspect(path, tool="apigx")
    assert result.returncode == 2, result.stdout
    assert "overrides the server path" in result.stderr and level in result.stderr


def test_a_document_without_servers_reports_no_base_rather_than_inventing_one(tmp_path):
    document = {
        "openapi": "3.0.3",
        "info": {"title": "X"},
        "paths": {"/v1/a": {"get": {"responses": {}}}, "/other/b": {"get": {"responses": {}}}},
    }
    path = tmp_path / "openapi.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    result = _inspect(path, "--json", tool="apigx")
    assert result.returncode in {0, 1}, result.stderr
    assert "base: /" in result.stdout or "base" not in result.stdout
    assert "unversioned-path" not in _codes(json.loads(result.stdout))


@pytest.mark.parametrize(
    ("tool", "document", "unhandled"),
    [
        (
            "apigx",
            {
                "openapi": "3.0.3",
                "info": {"title": "X"},
                "paths": {"/a": {"psot": {"responses": {}}}},
            },
            "a mistyped method, which would drop the route",
        ),
        (
            "apigx",
            {
                "openapi": "3.0.3",
                "info": {"title": "X"},
                "security": [{"bearer": []}],
                "paths": {"/a": {"post": {"securty": [], "responses": {"201": {}}}}},
            },
            "a mistyped security key, which would read as authenticated",
        ),
        (
            "apigx",
            {
                "openapi": "3.0.3",
                "info": {"title": "X"},
                "webhooks": {"ping": {"post": {"responses": {}}}},
                "paths": {"/a": {"get": {"responses": {}}}},
            },
            "declared operations outside paths",
        ),
        (
            "schemagx",
            "CREATE INDEX i ON a (x);\nCREATE TABLE a (id INT);\n",
            "a statement it does not translate",
        ),
        ("schemagx", "CREATE TABLE a (id INT) ENGINE=InnoDB;\n", "a clause it does not translate"),
        ("flowgx", "stateDiagram-v2\n    [*] --> a\n    a ~~> b\n", "a line it cannot read"),
    ],
)
def test_an_importer_refuses_what_it_cannot_account_for(tmp_path, tool, document, unhandled):
    """Silence is never a verdict: an unhandled construct must be refused.

    A converter that quietly narrows what it inspects reports success about a
    document it did not fully read, which is the failure this family exists to
    prevent. Each of these was reachable before: a mistyped method dropped a
    route, a mistyped `security` read as inherited authentication (hiding a
    public mutation), and an `ENGINE=` clause went unread.
    """
    path = tmp_path / "artifact"
    if isinstance(document, dict):
        path = path.with_suffix(".json")
        path.write_text(json.dumps(document), encoding="utf-8")
    else:
        path = path.with_suffix(".sql" if tool == "schemagx" else ".mmd")
        path.write_text(document, encoding="utf-8")
    result = _inspect(path, tool=tool)
    assert result.returncode == 2, f"{unhandled}: {result.stdout}{result.stderr}"
    assert "Traceback" not in result.stderr


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
    assert "not a Python artifact" in result.stderr and "Traceback" not in result.stderr
    assert "SyntaxError" not in result.stderr
