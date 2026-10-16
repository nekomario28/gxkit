# apigx, for AI agents

A person pointed you here. `apigx` checks that an HTTP API contract is safe
before you implement it: declare endpoints and the base path as a Python file,
then `apigx inspect` finds a route declared twice, a state-changing method with
no authentication, a path outside the versioned base, an endpoint documenting no
error, and deprecated routes — plus a storyboard.

This tool is part of `gxkit`; the review contract (`inspect`, `--json`, exit
codes, storyboard) is shared with every other tool in the family.

## Set it up

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/apigx" apigx --help
# or, from a clone:
uv tool install ./packages/apigx    # puts `apigx` on PATH
```

## The loop

1. **Write** the API as a `.py` file that builds an `API` (or defines
   `ENDPOINTS` / `BASE` / `NAME`).
2. **Inspect** — `apigx inspect api.py`. Prints the summary, every problem with a
   stable `code`, and writes `<name>.storyboard.png`.
   **Exit code 1 means at least one error.**
3. **Fix** and inspect again; look at the storyboard if you can view images.
4. **Render** — `apigx render api.py -o api.png`.

## Reading the report

- `error` — `duplicate-route` (the same method and path twice),
  `unauthenticated-mutation` (a POST/PUT/PATCH/DELETE with `auth=False`).
- `warn` — `path-outside-base` (a path not under the base).
- `info` — `no-error-status`, `deprecated-endpoint`, `no-endpoints`.

Common fixes: `duplicate-route` → drop one; `unauthenticated-mutation` → set
`auth=True` (in an OpenAPI document, `security: []` on the operation means
exactly this) or make it read-only; `path-outside-base` → move it under the base;
`no-error-status` → document the 4xx/5xx it can return. Use `--json` to branch on
the result.

`apigx inspect openapi.json` reads the OpenAPI 3 document a service publishes
instead of a declaration: paths and methods become endpoints, `security` becomes
authentication, numeric responses become statuses. A document that is not valid
OpenAPI 3 exits 2 and names where it is wrong. An unrecognised key in a path item
or an operation, a `webhooks` section, and a `$ref` are refused rather than
ignored, so a mistyped method or security key cannot quietly change the verdict.
