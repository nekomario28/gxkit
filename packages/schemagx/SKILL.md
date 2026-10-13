---
name: schemagx
description: Inspect a relational database schema for structural faults before code is written against it — foreign keys that name an unknown table or column, type mismatches between key columns, references to non-primary-key columns, foreign-key cycles that need deferred constraints, tables with no primary key, and orphan tables nothing uses. Declare tables, primary keys and foreign keys as data; get stable codes, exit codes, and an annotated storyboard. Use when designing or generating a database schema, ER model, or migration and you need to prove every reference resolves — especially when an agent is writing the DDL. Not for query style linting or for diffing two live databases.
---

# schemagx — prove a schema's references resolve

Part of the `gxkit` family; the review contract is shared with every `*gx` tool.

## Install

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
keys are `"table.column"` strings pointing child -> parent.

## The loop

1. Write the schema as a Python file.
2. `schemagx inspect schema.py` — tables, roots, problems with stable `code`s,
   and `<name>.storyboard.png`. **Exit 1 on any error.**
3. Fix and inspect again; the storyboard boxes each table at fault.
4. `schemagx render schema.py -o schema.png`.

## Severities

`error` = a reference does not resolve. `warn` = a type mismatch, a non-PK
reference, or a cycle needing deferred constraints. `info` = a missing primary
key or an orphan table.

## What it catches

| code | severity | meaning |
| --- | --- | --- |
| `dangling-foreign-key` | error | a foreign key names an unknown table or column |
| `fk-type-mismatch` | warn | the two columns have different types |
| `fk-to-non-primary-key` | warn | a foreign key points at a non-primary-key column |
| `cyclic-foreign-key` | warn | a foreign-key cycle — inserts need deferred constraints |
| `missing-primary-key` | info | a table has no primary key |
| `orphan-table` | info | nothing references the table and it references nothing |
| `no-tables` | info | the schema declares no tables |

Cycles come from `gxcore.graph.find_cycle`. Every check has a test that proves
it fires on a schema with the fault and stays quiet on one without (`tests/`).
