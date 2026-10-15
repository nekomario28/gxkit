# Shared gates

Retire A01–A03. The public `gxkit inspect` path must reject sys.exit(0/other),
continue a directory after a load failure, and execute each module once per
invocation without leaking a cache into the next call. Scope reuse in
`gxcore.loading`; preserve direct-tool behavior and public CLI help/version.

Baseline comparison must preserve duplicate findings and their stable domain
relationship identity. Use a new baseline format version and reject version 1
with an instruction to recreate it; do not guess identities from old messages.
Test added, removed and replaced relationships, numeric-message changes,
reordering, repeated findings and save/load/JSON through the public CLI.

Checkpoint: focused regressions red on the base, green on the repair; whole
suite still green. Human probe: inspect a directory containing an exiting file
followed by a bad seed manifest; expect exit 2 and the later report.
