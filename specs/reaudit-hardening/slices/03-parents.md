# Fail-closed recognized parents

Retire R03. Auxiliary collections inside a recognized shape are converted with
the same strict helper as their members: `references`, `goals` and
`auth_schemes` must be lists of names, and a member that is not a name is
rejected with its field and index. `resolve` may still fall back for an
unrelated shape, never for a recognized malformed one.

Checkpoint: the three reproduced parent fixtures exit 2, valid empty collections
still inspect their real findings, and every mutant that drops or coerces a
member is killed.
