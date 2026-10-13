"""A permission model with an escalation path and dead config.

  * ``user`` (low) reaches ``manage_users`` via editor            -> escalation
  * a grant names ``ghost``, an undeclared role                   -> dangling-grant
  * role ``auditor`` is assigned to nobody and inherited by nobody -> unreachable-role
  * permission ``export`` is granted to no role                   -> orphan-permission
"""

import authzgx as a

NAME = "Leaky blog permissions"

model = a.AuthModel(
    principals=["anonymous", "user", "admin"],
    roles=["viewer", "editor", "owner", "auditor"],
    permissions=["read", "write", "delete", "manage_users", "export"],
    grants=[
        ("viewer", "read"),
        ("editor", "write"),
        ("editor", "manage_users"),   # the leak
        ("owner", "delete"),
        ("ghost", "read"),            # undeclared role
    ],
    inherits=[("editor", "viewer")],
    assigned=[("user", "editor"), ("admin", "owner")],
    sensitive=["delete", "manage_users"],
    low=["user"],
)
