# Why the inspection gates are shaped the way they are

Rationale for two rounds of hardening: an audit of `v0.9.1` found eleven ways an
inspection could succeed without inspecting, and a reaudit of that work found
five more plus two guards that could not fail. The plan documents are gone; what
follows is what a reader needs in order to not undo them. The invariants are in
the code, and each is proven by a named regression and a bounded mutant.

## The one sentence

An inspector that reports success when it did not inspect is worse than no
inspector, because a green run is trusted. Every rule below exists to keep a
verdict and a failure distinguishable.

## Invariants

**A load failure is not a verdict.** Import and detection failures exit 2, never
0 or 1; a directory continues past a broken file instead of stopping. An artifact
that calls `sys.exit` is a load failure, including during detection. See
`gxcore/cli.py::run` and `gxkit/cli.py::_tool_for`.

**One execution per invocation, and the current source.** Routing and inspection
share one module execution (an invocation-scoped cache, never a persistent one),
and the source is compiled directly so a timestamp- and size-matched `.pyc`
cannot hide an edit. Compilation does not inherit the loader's future flags — a
flag in the loader must not change what the artifact means. See
`gxcore/loading.py::loading_session`, `load_module`.

**Inputs are absolute before anything executes.** An artifact may change the
process directory, so every requested path is resolved once, up front, and
routing, loading, configuration and reporting all use that identity. A relative
path that changes meaning mid-run is how two different files came to be inspected
under one name. See `gxkit/cli.py::_cmd_inspect`, `gxcore/cli.py::_cmd_inspect`.

**A recognized declaration fails closed.** If a shape is recognized and a member
is malformed, that is an `InvalidArtifact` naming the field and index — not a
fallback to another shape, not a dropped member, not a coercion. Name
collections use `convert_names` so a non-name is refused rather than stringified
into a name that matches nothing. See `gxcore/loading.py::convert_items`,
`convert_names`.

**Ambiguity is refused, not guessed.** A composite primary key, two initial
states in a diagram, a document holding several diagrams, OpenAPI 2, a note
block: each is refused with the line, because the model cannot hold it and
picking one silently would let a check state something untrue. See
`schemagx/ddl.py`, `flowgx/mermaid.py`, `apigx/openapi.py`.

**A rule has one owner.** "A cycle finding per cyclic component, identified by
that component" lives in `gxcore.graph.cycle_witnesses`; six tools report cycles,
and a single global search in any one of them hides the second component while
looking like a complete answer. The same reasoning made `convert_items` and
`convert_names` shared rather than per-tool.

**A baseline compares identity and multiplicity, not prose.** A finding is
identified by a domain-owned stable identity when its relationship is what
matters (a cron conflict partner, a network edge and endpoint); repeated findings
are preserved rather than collapsed into a set. Message wording, coordinates and
numeric prose are not identities. Format 2 rejects older baselines and asks for a
deliberate recreation instead of guessing. See `gxcore/baseline.py::fingerprint`,
`compare`.

**A report reaches the console it is printed on.** A message naming an arrow
must not turn a verdict into exit 2 on a code page that lacks it. See
`gxcore/cli.py::printable_output`.

**A guard must be shown failing.** Every rule above has a green control and a
named mutant that removes the rule and must be killed by that test's assertion,
not by a collection or import error. A check that reads a declaration instead of
the behaviour is not evidence. See `scripts/check_mutations.py` (52 mutants),
`scripts/guard_contracts.py` (the coverage gate is executed, and replayed with a
failing command), and `scripts/check_publish.py`.

**A declaration is not the world.** No tool claims runtime behaviour: seeds are
declarations, not reproducibility; schedules are declared occupancy, not what a
scheduler does; and the only thing that executes is a Python artifact, which is
documented rather than sandboxed. See `docs/CONTRACT.md` and
`SECURITY.md`.

## Limits worth keeping honest

The mutation catalogue is bounded: it proves the named defects cannot return, not
that no defect exists. The sixteen domains have not each been exhaustively
audited. Reading a document is a parser, and each importer names what it refuses
so a reader can tell "clean" from "not understood".
