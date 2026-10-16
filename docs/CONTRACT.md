# The contract

What an integrator may rely on, and what it may not. This is the document a
v1.0 claim rests on: everything listed as stable is covered by a test, and
everything listed as unstable is explicitly not promised.

## Stable

These will not change without a major version bump.

**Problem codes.** Every problem carries a `code` from a fixed, documented set.
`gxkit codes` prints that set with each code's severity; `docs/TRACE.md` is the
generated tool→module→codes table, whose column is a *count* per tool. Codes are the
branch point; message prose is not. A code's severity is stable within a major
version, and severities only ever move from `info` to `warn` to `error` — never
the other way, because that would silently weaken an existing gate.

**Exit codes.** Every tool, and the umbrella:

| code | meaning |
| --- | --- |
| 0 | inspected, no `error` |
| 1 | inspected, at least one `error` (or, with `--baseline`, at least one *new* error) |
| 2 | the input could not be inspected: missing, unreadable, malformed, it called `sys.exit`, or the tool needs a capability this machine does not have (a missing `ffprobe`) — the refusal names what is missing |

A `warn` or `info` never fails a build.

**The JSON report.** `--json` prints `name`, `subject`, `details`, `errors`,
`problems` (each with `severity`, `code`, `message`, and `target`/`label`/
`identity` when present), plus `storyboard` and `baseline` when they apply. Keys
are only ever added.

**The baseline.** `--write-baseline` / `--baseline` compare a run to an accepted
state and report `new`, `fixed`, `persisted`, `new_errors`. Format 2 is current
and preserves repeated findings and explicit relationship identities; an older
format is rejected rather than guessed at. A baseline whose shape cannot be read
is refused with the offending field and index, because a record that never
matches would report every finding as fixed or new.

**The config.** `.gxkit.toml` accepts `ignore`, `severity`, and per-tool tables
of the same two keys. Anything else is refused with its field — including
`ignore = "code"` (a string, which would otherwise mean the characters it
contains), a severity that is not `error`/`warn`/`info`, and a mistyped key in a
tool table. Reading a configuration that cannot be understood and then inspecting
anyway is the silent-narrowing failure this contract forbids.

**The CLI shape.** `<tool> inspect <path>` and `<tool> render <path>`, with
`--json`, `--no-storyboard`, `-o/--output`, `--baseline`, `--write-baseline` and
`--no-config`. The umbrella adds `tools` and `codes`.

**Supported Python.** 3.10 through 3.13, on Linux, macOS and Windows.

**Inputs.** Every tool takes a Python file, and four also take a document:

| tool | also takes | and what it does with it |
| --- | --- | --- |
| `apigx` | `.json` | an OpenAPI 3 document, converted to the same model |
| `schemagx` | `.sql` | SQL DDL, converted to the same model |
| `flowgx` | `.mmd`, `.mermaid`, `.md`, `.markdown` | a Mermaid state diagram, or the one `stateDiagram` block a document holds |
| `chartgx` | `.json` | a chart declared as data (a figspec model): inspected without matplotlib and without running anything. It has no storyboard here — the renderer that owns the model draws one (`figspec storyboard`), and `-o` on such a declaration is refused rather than silently skipped |

`chartgx` runs any Python script that builds a matplotlib figure, and `framegx`
probes the video a Python declaration points at; both still take a Python file.
The suffixes each tool accepts are declared in `gxkit.registry`, printed by
`gxkit tools --json`, listed in `docs/TRACE.md`, and used to name the tool when a
document that is not Python is passed.

A Python artifact is detected automatically; a document that is not Python needs
its tool named, because detection reads a Python module. Reading a document adds
no runtime dependency and no code path that executes it — a foreign document is
parsed as data. A construct the importer cannot represent is refused with its
location rather than guessed at: OpenAPI 2, a `$ref`, an unrecognised key, a
server override that changes the path, a composite key, an unterminated comment
or literal, a composite or ambiguous diagram.

## Not stable

Do not build on these; they may change in a minor version.

- **Message prose.** It is written for a reader. Two messages may name the same
  finding differently after a wording improvement.
- **Problem order within a severity.** Errors come first, then by target, but
  the order among equal targets is not a contract.
- **Storyboard pixels.** The image is evidence for a human: the boxes and
  numbers follow the text report, but no coordinate, size or colour is promised.
- **Which codes a tool can emit.** The set is documented per tool and grows; a
  new code may appear in a minor version (which is why a baseline exists).
- **Importable Python API.** `load_*`, `inspect_*`, `*_from_parts` and the model
  dataclasses are public and useful, but only the CLI contract above is
  guaranteed.
- **Capability-bound behaviour.** `shadergx` needs a GL context and `framegx`
  needs `ffmpeg`. Where a capability is absent the affected tests skip, and the
  tool does one of two measured things: it **refuses the input with exit 2** naming
  the missing program (`framegx` without `ffprobe` — measured), or it **reports
  what it can still determine** (a GL driver that cannot compile the shader's
  features is a `compile-error`, not a refusal). Which of the two happens is a
  property of where the capability is missing, not of the artifact.

## Silence is never a verdict

A tool reports a finding or refuses the input. It never narrows what it read and
then reports success about the part it skipped, and importers enforce this the
same way: an unrecognised key, a statement outside the translated set, or a
reference that would have to be followed are all refused with their location
rather than ignored.

Where a construct is recognised but the model has no place for it, it is
**reported as not carried** (`schemagx`'s `not-modelled`: `NOT NULL`, `DEFAULT`,
`UNIQUE`, `CHECK` and the rest are named per table while reference integrity is
still checked) — refused or reported, never ignored. A document that reads as
clean has been fully read.

Where an importer can express more than the model, the refusal names the limit
(a composite key, a composite or ambiguous diagram, OpenAPI 2, a `$ref`) instead
of guessing — see each tool's `AGENTS.md`.

## What this is not

- **Not a conformance validator.** Reading an OpenAPI document or a SQL dump
  means implementing that format's semantics, and nothing here verifies that
  implementation against the specification. A wrong reading of a format is a
  bug in this repository, found by review and tests, not by these tools: gxkit
  inspects *artifacts*, not the code that reads them.
- **Not a checker for this repository.** The family's own structure is held by
  tests, the bounded mutation catalogue, the package and consumer gates, and a
  `depsgx` run over its own module graph (`scripts/self_inspect.py`). Those find
  structural regressions; they do not tell you whether a check is *correct*.
- **Not a runtime or quality oracle.** A clean report means the declared
  structure is coherent, not that the artifact works, looks right, or is
  reproducible.

## Inspection, not sandboxing

A Python artifact is executed to be inspected. That is the design: the artifact
declares itself by building an object. It is not a security boundary — inspect
artifacts you trust, exactly as you would run them. A foreign document
(an OpenAPI file) is parsed as data and never executed.

## Declaration versus behaviour

A tool inspects what an artifact *declares*. `seedgx` checks that seeds are
declared, not that a run is reproducible; `crongx` checks declared occupancy,
not what a scheduler does. No tool claims to have verified runtime behaviour,
rendered output quality, or infrastructure.

## Support

MIT licensed. The repository's CI runs the full suite, a 100% statement-coverage
floor, bounded mutation proofs and an isolated installation of the published
artifacts on every change, so a green `main` means those gates hold for that
revision. It does not mean every domain has been exhaustively audited.
