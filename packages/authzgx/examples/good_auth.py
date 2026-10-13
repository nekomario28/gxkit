"""A permission model that should pass: no low principal reaches a sensitive permission.

`user` gets `read` and `write` through `editor`/`viewer`; `delete` and
`manage_users` sit behind `owner`, which only `admin` holds. `anonymous` holds
nothing.
"""

import authzgx as a

NAME = "Blog permissions"

model = a.AuthModel(
    principals=["anonymous", "user", "admin"],
    roles=["viewer", "editor", "owner"],
    permissions=["read", "write", "delete", "manage_users"],
    grants=[
        ("viewer", "read"),
        ("editor", "write"),
        ("owner", "delete"),
        ("owner", "manage_users"),
    ],
    inherits=[("editor", "viewer"), ("owner", "editor")],
    assigned=[("user", "editor"), ("admin", "owner")],
    sensitive=["delete", "manage_users"],
    low=["anonymous", "user"],
)
