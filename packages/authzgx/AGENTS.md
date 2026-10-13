# authzgx, for AI agents

A person pointed you here. `authzgx` checks a permission model for privilege
escalation and dead config before it ships: declare principals, roles,
permissions and how they connect, then `authzgx inspect` proves what each
principal can reach — and whether a low-privilege one can reach something
sensitive.

Part of `gxkit`; the review contract (`inspect`, `--json`, exit codes,
storyboard) is shared with every other tool in the family.

## Set it up

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/authzgx" authzgx --help
uv tool install ./packages/authzgx
```

## Write a model

```python
import authzgx as a

model = a.AuthModel(
    principals=["anonymous", "user", "admin"],
    roles=["viewer", "editor", "owner"],
    permissions=["read", "write", "delete"],
    grants=[("viewer", "read"), ("editor", "write"), ("owner", "delete")],
    inherits=[("editor", "viewer"), ("owner", "editor")],
    assigned=[("user", "editor"), ("admin", "owner")],
    sensitive=["delete"],
    low=["anonymous", "user"],
)
```

Or module-level `PRINCIPALS` / `ROLES` / `PERMISSIONS` / `GRANTS` / `INHERITS` /
`ASSIGNED` / `SENSITIVE` / `LOW`.

## The loop

1. **Write** the model as a `.py` file.
2. **Inspect** — `authzgx inspect auth.py`. It prints what each principal
   reaches, the escalation path if any, and every problem with a stable `code`,
   and writes `<name>.storyboard.png`. **Exit 1 means at least one error.**
3. **Fix** and inspect again. View the storyboard: each numbered box marks a
   role/permission at fault.
4. **Render** — `authzgx render auth.py -o auth.png`.

## Reading the report

- `error` — a real problem: `escalation` (a low principal reaches a sensitive
  permission, with the path), `cyclic-inheritance`, or a dangling reference.
  Exit code 1.
- `info` — dead config: an unreachable role, an orphan permission, an empty role.

Set `sensitive` and `low` to make escalation meaningful: `low` are the
principals that must **not** reach any `sensitive` permission.
