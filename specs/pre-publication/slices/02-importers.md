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

**`flowgx` reads a Mermaid state diagram.** `[*] --> s` is the start,
`s --> [*]` is accepting, and `a --> b : event` is a transition; a `.mmd` file is
read directly, and a Markdown document through the one `stateDiagram` block it
holds. Two initial states, a composite state and a document with more than one
diagram are refused with their line, because `Machine` has one start and no
hierarchy, and which diagram is the artifact is not worth guessing.

All three are checked by the same codes as a declaration, and each is proven
through the public CLI and by mutants for its routing, markers, refusal branches
and malformed input.

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

`shadergx` + a bare `.frag` file was considered and deferred, not rejected: it is
equally faithful (a shader file is the artifact, with no wrapper to write), but
its audience is narrower than the state diagrams teams keep in their docs, and
installation weight is the same either way. Add it when someone asks for it.

## What the independent review changed

A review of the three importers found five ways they could be silently wrong, and
all five were reproduced and repaired:

- **An anonymous security alternative read as authenticated** (the finding of
  record). `security: [{}]` requires nothing, and alternatives are ORed, so a
  public mutating route was reported as authenticated — a false negative on the
  one check that is about exposure.
- **The server path ignored.** OpenAPI defines an endpoint as the server's path
  followed by the path item, so comparing an unprefixed path against the base
  reported a correctly versioned endpoint as unversioned.
- **An intervening statement skipped.** Searching for the next `CREATE TABLE`
  meant an `ALTER` between two tables disappeared, against the documented
  promise that anything else is refused with its line.
- **An omitted reference column invented as `id`.** SQL means the referenced
  table's primary key, whatever it is called; the importer now resolves it after
  every table is read, and refuses when there is none to mean.
- **A referenced path item dropped.** A `$ref` path item produced no methods and
  vanished, so a document could report no endpoints while hiding an
  unauthenticated mutation. References are refused, not resolved.

Each repair has a named regression and a mutant (the catalogue is 57).
>>>>>>> b201449 (Fix what the importer review found, and close the hygiene items)
