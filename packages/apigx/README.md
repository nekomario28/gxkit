# apigx

**Inspect an HTTP API contract for duplicate routes, unauthenticated mutations
and unversioned paths.** Declare endpoints and the base path; `apigx inspect`
finds a route declared twice, a state-changing method with no authentication, a
path outside the versioned base, an endpoint documenting no error, and
deprecated routes.

One of the [`gxkit`](../../README.md) tools, built on [`gxcore`](../gxcore).

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/apigx" apigx inspect api.py
# local:  uvx --from ../../packages/apigx apigx inspect api.py
```

## Writing an API

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

An endpoint is `(method, path)` or a mapping with `auth`, `statuses` and
`deprecated`. Or module-level `ENDPOINTS` / `BASE` / `NAME`.

Or point it at the OpenAPI 3 document your service already publishes:

```sh
apigx inspect openapi.json
```

Paths and methods become endpoints, an operation's `security` becomes its
authentication, its numeric responses become the documented statuses, and the
first server's path becomes the base — with each operation path prefixed by it,
as OpenAPI defines. Security is read as OpenAPI means it: a missing `security`
inherits the document's, `[]` requires none, and an empty requirement (`[{}]`) is
an alternative that requires nothing, so a route listing it is public however many
schemes stand beside it. The same codes then apply — an
unauthenticated mutation in a published spec is the same defect as one in a
declaration. OpenAPI 2 / Swagger is not supported, and a document that is not
valid OpenAPI 3 is an input failure (exit 2) that names where it is wrong.

The base is what the document declares in `servers`, and every operation path is
built in that coordinate space. A path-item or operation `servers` that changes
the path is refused, because the model carries one base for the whole API.

`unversioned-path` is a check on a *declaration*: an imported spec declares its
own base, so every path is under it by construction and the check cannot fire.

Nothing is ignored: a key the importer does not recognise in a path item or an
operation, a `webhooks` section, and a `$ref` that would have to be followed are
all refused. That is deliberate — a mistyped method would otherwise drop a route,
and a mistyped `security` would read as inherited authentication and hide a
public mutation.

Names are names: `auth_schemes` must be a list of strings. A malformed member
or collection rejects the artifact with its field and index (exit 2) instead
of disappearing, and a recognized declaration is never replaced by another.

## The contract

```
$ apigx inspect broken_api.py
broken_api.py: Broken API
api: 5 endpoints
storyboard: Broken_API.storyboard.png
  5 endpoints
  base: /v1
inspect: 5 problems (2 errors)
  [1] error ep[1]      duplicate-route: GET /v1/users is declared twice
  [2] error ep[2]      unauthenticated-mutation: POST /users changes state but requires no authentication
  [3] warn  ep[2]      unversioned-path: /users is not under the base '/v1'
  [4] info  ep[3]      no-error-status: PATCH /v1/users/{id} documents no error status (4xx/5xx)
  [5] info  ep[4]      deprecated-endpoint: GET /v1/legacy is deprecated
```

- **Exit code 1** when any `error`-severity problem is found.
- `--json` prints the same report machine-readably; `--no-storyboard` skips the
  image; `-o name.png` names it.

## Checks

| code | severity | what it means |
| --- | --- | --- |
| `duplicate-route` | error | the same method and path declared twice |
| `unauthenticated-mutation` | error | a POST/PUT/PATCH/DELETE with `auth=False` |
| `unversioned-path` | warn | a path not under the base |
| `no-error-status` | info | an endpoint documents no 4xx/5xx |
| `deprecated-endpoint` | info | an endpoint is marked deprecated |
| `no-endpoints` | info | the API declares no endpoints |

## Why it can be trusted

Every check is proven to fire on an API with the fault and to stay quiet on one
without (`tests/`). The route lookup is the same idea `schemagx` uses for keys.

MIT licensed.
