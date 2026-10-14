"""An API that should pass: versioned, authenticated mutations, documented errors."""

import apigx as a

NAME = "Users API"

api = a.API(
    base="/v1",
    endpoints=[
        a.Endpoint("GET", "/v1/users", statuses=[200, 404]),
        a.Endpoint("POST", "/v1/users", auth=True, statuses=[201, 400, 409]),
        a.Endpoint("DELETE", "/v1/users/{id}", auth=True, statuses=[204, 404]),
    ],
)
