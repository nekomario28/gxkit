# Read the file people already have

An importer converts a foreign document into the tool's own model. It never
widens what a check claims, and it adds no runtime dependency.

**`apigx` reads an OpenAPI 3 document.** Paths and methods become endpoints,
`security` becomes the authentication requirement (inherited from the document
when absent, and an empty list meaning "requires none"), numeric responses become
the documented statuses, and the first server's path becomes the base. OpenAPI 2
is refused rather than guessed at, and a malformed document exits 2 naming where
it is wrong.

**`schemagx` reads SQL DDL.** `CREATE TABLE` becomes tables, `PRIMARY KEY` and
`FOREIGN KEY ... REFERENCES` become the keys, and column types are compared by
family, so a PostgreSQL `SERIAL` key with an `INTEGER` reference is not a
mismatch. A composite key and anything that is not `CREATE TABLE` are refused
with their line: `Schema` records one primary key per table and one column per
foreign key, and picking one silently would let a check state something untrue.

Both are checked by the same codes as a declaration, and both are proven through
the public CLI and by mutants for their authentication, version, malformed-input,
routing and refusal branches.

Checkpoint: a published spec with an unauthenticated POST, and a dump with a
foreign key to a non-primary key, are both reported by the public CLI; a
composite key exits 2 naming the table rather than reporting a wrong verdict.

## Why not the other two candidates

`envgx` + `.env` was rejected: the check's premise is that a *declaration* in
source carries a default, while a `.env` file legitimately holds secret values,
so who-every-variable-is-unused unless a references side is also declared. A
`.env` importer would either flood false errors or need a source scan, which is a
different feature.

`depsgx` + `pyproject.toml` was rejected: a dependency list is acyclic by
construction and has no layers, so the graph checks that make `depsgx` useful
have nothing to say about it.
