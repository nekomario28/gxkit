# Reaudit hardening

## Goal

Repair the five reproduced PR #3 findings. Four are defect classes the
hardening pass left open, one is a guard that cannot fail. Every repair must be
demonstrated red on the reaudit head and green after its fix, and the two guard
repairs must be mutation-proven in the same catalogue as the product defects.

Findings:

- R01 a replaced network relationship is accepted as existing baseline debt.
- R02 a relative input path can inspect a different artifact after cwd changes.
- R03 invalid recognized parent declarations fall back to clean alternatives.
- R04 a coverage-disabling environment passes the executable-argv guard.
- R05 a swallowed pytest failure passes the same guard.

## Ownership and contracts

- `netgx.checks` owns relationship identity. `gxcore.baseline` compares
  identities and multiplicities; it never invents a relationship identity.
- `gxkit.cli` owns the invocation's input identities. An artifact's own cwd
  change must not redirect routing or inspection to another file.
- `gxcore.loading` owns strict recognized declarations. A recognized shape with
  an invalid member is an `InvalidArtifact`, never another shape.
- `scripts/guard_contracts.py` proves the coverage gate can fail. It observes
  executed commands *and* the environment they execute in, then replays a
  failing command to require failure to propagate.
- Display names may stay relative; load identity must be absolute.

## Non-goals

No new tool, no release, no merge, no baseline v3, no sandbox claim, no
exhaustive all-domain conversion rewrite. Unrelated `list(...)` coercions
outside the reproduced findings are recorded, not silently expanded.

## Evidence ledger

Reaudit report: the reaudit `REPORT.md` kept beside its probe logs outside the
repository. Reproductions live in `results.json`, `base-comparison.json` and
`guard-nodes.json`; the base comparison proves R01–R03 predate the hardening
branch and R04–R05 are new-guard blind spots. Full logs belong outside the
repository; decisions belong in [choices](choices.md).

One further defect surfaced while proving these repairs rather than in the
reaudit itself: a message naming an edge arrow could not be printed on a console
whose code page lacks it, so a real verdict exited 2 on Windows. It is repaired
with the five findings and recorded here because it was found by their tests.

## Slices

- [x] [1. Relationship identity](slices/01-identity.md): R01.
- [x] [2. Invocation identities](slices/02-paths.md): R02.
- [x] [3. Parent declarations](slices/03-parents.md): R03.
- [x] [4. Gate that can fail](slices/04-gate.md): R04, R05.
- [x] [5. Proof and verification](slices/05-verification.md).
