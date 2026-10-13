# schemagx, for AI agents

A person pointed you here. `schemagx` checks a relational schema before code is
written against it: declare tables, primary keys and foreign keys, then
`schemagx inspect` proves every reference resolves and finds structures that
will bite (cycles, dead tables).

Part of `gxkit`; the review contract (`inspect`, `--json`, exit codes,
storyboard) is shared with every other tool in the family.

## Set it up

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/schemagx" schemagx --help
uv tool install ./packages/schemagx
```

## Write a schema

```python
import schemagx as s

schema = s.Schema(
    tables={
        "users": {"id": "int", "email": "text"},
        "posts": {"id": "int", "author_id": "int"},
    },
    primary_keys={"users": "id", "posts": "id"},
    foreign_keys=[("posts.author_id", "users.id")],
    roots=["users"],
)
```

Or module-level `TABLES` / `PRIMARY_KEYS` / `FOREIGN_KEYS` / `ROOTS`. Foreign
keys are `"table.column"` strings and point child -> parent.

## The loop

1. **Write** the schema as a `.py` file.
2. **Inspect** — `schemagx inspect schema.py`. It prints the tables, roots and
   every problem with a stable `code`, and writes `<name>.storyboard.png`.
   **Exit 1 means at least one error.**
3. **Fix** and inspect again. View the storyboard: each numbered box marks a
   table at fault.
4. **Render** — `schemagx render schema.py -o schema.png`.

## Reading the report

- `error` — a reference does not resolve (`dangling-foreign-key`). Exit code 1.
- `warn` — a type mismatch, a non-primary-key reference, or a foreign-key cycle
  that will need deferred constraints.
- `info` — a missing primary key or an orphan table.
