"""An API with faults.

* `GET /v1/users` is declared twice                  -> duplicate-route
* `POST /users` changes state with no auth            -> unauthenticated-mutation
* `POST /users` is outside the /v1 base               -> unversioned-path
* `PATCH /v1/users/{id}` documents no error status     -> no-error-status
* `GET /v1/legacy` is deprecated                       -> deprecated-endpoint
"""

import apigx as a

NAME = "Broken API"

api = a.API(
    base="/v1",
    endpoints=[
        a.Endpoint("GET", "/v1/users", statuses=[200, 404]),
        a.Endpoint("GET", "/v1/users", statuses=[200, 404]),
        a.Endpoint("POST", "/users", auth=False, statuses=[201, 400]),
        a.Endpoint("PATCH", "/v1/users/{id}", auth=True, statuses=[]),
        a.Endpoint("GET", "/v1/legacy", statuses=[200, 410], deprecated=True),
    ],
)
