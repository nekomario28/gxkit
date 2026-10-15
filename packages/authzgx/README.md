# authzgx

**Inspect permission models for privilege-escalation paths.** Declare
principals, roles, permissions and how they connect; `authzgx inspect` computes
what each principal can reach and proves whether a low-privilege principal can
reach a sensitive permission — with the path, not a guess.

One of the [`gxkit`](../../README.md) tools, built on [`gxcore`](../gxcore).

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/authzgx" authzgx inspect auth.py
# local:  uvx --from ../../packages/authzgx authzgx inspect auth.py
```

## Writing a model

```python
import authzgx as a

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
    inherits=[("editor", "viewer"), ("owner", "editor")],  # child gets parent's perms
    assigned=[("user", "editor"), ("admin", "owner")],
    sensitive=["delete", "manage_users"],
    low=["anonymous", "user"],
)
```

Or module-level `PRINCIPALS` / `ROLES` / `PERMISSIONS` / `GRANTS` / `INHERITS` /
`ASSIGNED` / `SENSITIVE` / `LOW`.

A principal *reaches* a permission when a role it holds grants it or inherits
(transitively) from one that does. That is reachability on one graph
(`principal → role → parent role → permission`).

## The contract

```
$ authzgx inspect escalate_auth.py
escalate_auth.py: Leaky blog permissions
auth: 3 principals, 4 roles, 5 permissions
storyboard: Leaky_blog_permissions.storyboard.png
  3 principals, 4 roles, 5 permissions
  sensitive: delete, manage_users
  low: user
  user effective: manage_users, read, write
inspect: 5 problems (2 errors)
  [1] error -          dangling-grant: grant names unknown role 'ghost'
  [2] error perm:manage_users escalation: low principal 'user' reaches sensitive permission
      'manage_users' via user → editor → manage_users
  ...
```

- **Exit code 1** when any `error`-severity problem is found.
- `--json` prints the same report machine-readably; `--no-storyboard` skips the
  image; `-o name.png` names it.

## Checks

| code | severity | what it means |
| --- | --- | --- |
| `escalation` | error | a low principal reaches a sensitive permission (path given) |
| `cyclic-inheritance` | error | role inheritance has a cycle; one finding per cyclic component |
| `dangling-grant` / `dangling-assignment` / `dangling-inherit` | error | a reference names something undeclared |
| `unreachable-role` | info | no principal can reach the role |
| `orphan-permission` | info | no role grants the permission |
| `unreachable-permission` | info | no principal can reach the permission |
| `empty-role` | info | the role grants nothing, directly or by inheritance |
| `no-sensitive` / `no-low` / `no-permissions` | info | escalation cannot be judged,
  or the model declares no permissions |

## Why it can be trusted

Every check is proven to fire on a model with the fault and to stay quiet on one
without (`tests/`), and the escalation path is a real shortest path through the
graph — the same `gxcore.graph` that finds soft-locks in a game level.

MIT licensed.
