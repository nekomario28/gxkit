---
name: apigx
description: Use when an agent has written an HTTP API contract (endpoints plus a base path) and must check it before implementing — a duplicate route, a state-changing method with no authentication, a path outside the versioned base, an endpoint documenting no error, or a deprecated route. Provides `apigx inspect` with stable codes, an exit code, `--json` and a storyboard. Part of the gxkit family.
---

# apigx

`apigx` reads an HTTP API contract written as data and reports what is wrong
before anyone implements it.

## Use it

```sh
uv tool install "git+https://github.com/nekomario28/gxkit#subdirectory=packages/apigx"
apigx inspect api.py            # report + storyboard; exit 1 on any error
apigx inspect api.py --json
apigx render  api.py -o api.png
```

Write the API as a Python file:

```python
import apigx as a

api = a.API(
    base="/v1",
    endpoints=[
        a.Endpoint("GET", "/v1/users", statuses=[200, 404]),
        a.Endpoint("POST", "/v1/users", auth=True, statuses=[201, 400]),
    ],
)
```

An endpoint is `(method, path)` or a mapping with `auth`, `statuses`,
`deprecated`. Or module-level `ENDPOINTS` / `BASE` / `NAME`.

## What it catches

| code | severity | what it means |
| --- | --- | --- |
| `duplicate-route` | error | the same method and path declared twice |
| `unauthenticated-mutation` | error | a POST/PUT/PATCH/DELETE with `auth=False` |
| `path-outside-base` | warn | a path not under the base |
| `no-error-status` | info | an endpoint documents no 4xx/5xx |
| `deprecated-endpoint` | info | an endpoint is marked deprecated |
| `no-endpoints` | info | the API declares no endpoints |

## Why the checks can be trusted

Every check has a test that builds the defect and asserts it fires, and one that
asserts an honest API stays quiet (`packages/apigx/tests/`).

## Where it fits

Part of `gxkit`; the `inspect` contract (stable codes, exit codes, `--json`, a
storyboard) is shared. See the family skill at the repository root.
