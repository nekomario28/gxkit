# Pre-publication goals

## Goal

Make the family publishable and reachable. Everything below is work that must
land *before* a PyPI release; the release itself needs the owner's credentials
and stays a separate action.

The blocker is not quality — the gates are strict and green — it is the entrance:
the only install route is Git, one tool cannot read a file people already have,
and nothing has proven that the eighteen distributions resolve from an index.

- [x] [1. Index dry run](slices/01-index.md): prove the family installs from a
  local index in publish order, with no workspace sources.
- [x] [2. A file people already have](slices/02-importers.md): `apigx` reads an
  OpenAPI document instead of asking for a transcription.
- [x] [3. One entrance per reader](slices/03-entrances.md): lead with the
  single-tool route, keep the family route whole, publish the contract.
- [x] [4. Proof](slices/04-verification.md).

## Ownership and contracts

- `scripts/release.py` owns the publish plan and the distribution check;
  `scripts/check_publish.py` owns proving that plan resolves from an index.
- A domain tool owns what it can read. An importer converts a foreign document
  into the tool's own model and is checked by the same codes as a declaration;
  it never widens what a check claims.
- `docs/CONTRACT.md` owns what an integrator may rely on. Codes, severities, exit
  codes, JSON keys and baseline format 2 are stable; message prose, storyboard
  pixels and per-tool code sets are not.
- The umbrella keeps its promise of one entry point for the whole family. A
  single-purpose reader is served by the tool's own distribution.

## Non-goals

No new domain tool before adoption evidence. No PyPI publication, tag or release
note without explicit authorization. No change to codes, severities, exit codes,
JSON keys or baseline format. No runtime dependency added for an importer: the
standard library reads these documents.

## Evidence ledger

The reaudit proved the family accepts its own module graph; the self-inspection
harness stays in the repository root so no distribution carries it. The Git
consumer route is proven at an immutable revision; before publication the index
route must be proven too, because a family that resolves from Git can still fail
to resolve from an index when one package's range is wrong.

Decisions belong in [choices](choices.md). The architecture the importers and
gates rest on is recorded as durable rationale in
[`../done/inspection-correctness-hardening.md`](../done/inspection-correctness-hardening.md).

Staged and verified for the release: every package at **1.0.0** with
`gxcore>=1.0,<2.0` in consumers, the CHANGELOG consolidated into one `[1.0.0]`
release section, and `docs/RELEASING.md` carrying the exact order of steps.

Remaining, and owned by the repository owner: the PyPI token, `uv publish` in
dependency order, and the `v1.0.0` tag and release whose body is extracted from
the CHANGELOG.
