# The contract

What an integrator may rely on, and what it may not. This is the document a
v1.0 claim rests on: everything listed as stable is covered by a test, and
everything listed as unstable is explicitly not promised.

## Stable

These will not change without a major version bump.

**Problem codes.** Every problem carries a `code` from a fixed, documented set
(`gxkit codes`, or `docs/TRACE.md` for the generated table). Codes are the
branch point; message prose is not. A code's severity is stable within a major
version, and severities only ever move from `info` to `warn` to `error` — never
the other way, because that would silently weaken an existing gate.

**Exit codes.** Every tool, and the umbrella:

| code | meaning |
| --- | --- |
| 0 | inspected, no `error` |
| 1 | inspected, at least one `error` (or, with `--baseline`, at least one *new* error) |
| 2 | the input could not be inspected: missing, unreadable, malformed, or it called `sys.exit` |

A `warn` or `info` never fails a build.

**The JSON report.** `--json` prints `name`, `subject`, `details`, `errors`,
`problems` (each with `severity`, `code`, `message`, and `target`/`label`/
`identity` when present), plus `storyboard` and `baseline` when they apply. Keys
are only ever added.

**The baseline.** `--write-baseline` / `--baseline` compare a run to an accepted
state and report `new`, `fixed`, `persisted`, `new_errors`. Format 2 is current
and preserves repeated findings and explicit relationship identities; an older
format is rejected rather than guessed at.

**The CLI shape.** `<tool> inspect <path>` and `<tool> render <path>`, with
`--json`, `--no-storyboard`, `-o/--output`, `--baseline`, `--write-baseline` and
`--no-config`. The umbrella adds `tools` and `codes`.

**Supported Python.** 3.10 through 3.13, on Linux, macOS and Windows.

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
  needs `ffmpeg`; where they are absent the affected tests skip and the tool
  reports what it can still determine.

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
