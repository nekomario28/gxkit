# schemagx

**Inspect a relational schema for dangling keys, foreign-key cycles and dead
tables.** Declare tables, primary keys and foreign keys; `schemagx inspect`
checks every reference resolves, finds cycles that need deferred constraints,
and points at tables nothing uses.

One of the [`gxkit`](../../README.md) tools, built on [`gxcore`](../gxcore).

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/schemagx" schemagx inspect schema.py
# local:  uvx --from ../../packages/schemagx schemagx inspect schema.py
```

## Writing a schema

```python
import schemagx as s

schema = s.Schema(
    tables={
        "users": {"id": "int", "email": "text"},
        "posts": {"id": "int", "author_id": "int", "title": "text"},
    },
    primary_keys={"users": "id", "posts": "id"},
    foreign_keys=[("posts.author_id", "users.id")],  # "table.column"
    roots=["users"],
)
```

Or module-level `TABLES` / `PRIMARY_KEYS` / `FOREIGN_KEYS` / `ROOTS`. Foreign
keys point from the referencing (child) table to the referenced (parent) table.

Or point it at the SQL DDL your database already has:

```sh
schemagx inspect schema.sql
```

`CREATE TABLE` becomes tables, `PRIMARY KEY` (inline or table-level) becomes the
primary key, and `FOREIGN KEY ... REFERENCES` (inline or table-level) becomes the
foreign key — the same codes then apply, so a foreign-key cycle in a dump is the
same defect as one in a declaration. Column types are compared by family, so a
PostgreSQL `SERIAL` key with an `INTEGER` reference is not a mismatch. Two limits
are refused rather than guessed at: a composite primary or foreign key (the model
records one column per key), and any statement that is not `CREATE TABLE` — both
reported with their line.

## The contract

```
$ schemagx inspect broken_schema.py
broken_schema.py: Tangled schema
schema: 5 tables, 7 foreign keys
storyboard: Tangled_schema.storyboard.png
  5 tables, 7 foreign keys
  roots: users
  cyclic tables: {posts, tags}
inspect: 10 problems (4 errors)
  [1] error -          dangling-foreign-key: 'ghost.id' references unknown table 'ghost'
  [2] error legacy     dangling-foreign-key: 'legacy.owner' references unknown column 'owner'
  [3] error posts      dangling-foreign-key: 'posts.draft_id' references unknown column 'draft_id'
  ...
```

- **Exit code 1** when any `error`-severity problem is found.
- `--json` prints the same report machine-readably; `--no-storyboard` skips the
  image; `-o name.png` names it.

## Checks

| code | severity | what it means |
| --- | --- | --- |
| `dangling-foreign-key` | error | a foreign key names an unknown table or column |
| `fk-type-mismatch` | warn | the two columns have different types |
| `fk-to-non-primary-key` | warn | a foreign key points at a non-primary key column |
| `cyclic-foreign-key` | warn | a foreign-key cycle — inserts need deferred constraints |
| `missing-primary-key` | info | a table has no primary key |
| `orphan-table` | info | nothing references the table and it references nothing |
| `no-tables` | info | the schema declares no tables |

## Why it can be trusted

Every check is proven to fire on a schema with the fault and to stay quiet on
one without (`tests/`). Foreign-key cycles come from `gxcore.graph.find_cycle`.

MIT licensed.
