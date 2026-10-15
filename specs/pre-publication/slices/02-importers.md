# Read the file people already have

`apigx` loads an OpenAPI 3 document: paths and methods become endpoints,
`security` becomes the auth requirement, responses become documented statuses,
and `deprecated` survives. The same codes then apply — an unauthenticated
mutation in a published spec is the same defect as one in a declaration.

An importer converts a foreign document into the tool's own model. It never
widens what a check claims, and it adds no runtime dependency.

Checkpoint: a real OpenAPI document with an unauthenticated POST and a path
outside the base is reported by the public CLI, and a malformed document exits 2
with its location rather than a traceback.
