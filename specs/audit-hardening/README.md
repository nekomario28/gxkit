# Inspection correctness hardening

## Goal

Fix the eleven reproduced v0.9.1 audit findings before adding another domain.
Every regression must fail on the audited revision and pass after its repair.
Finish with strict local gates, independent review, remote CI, and an isolated
consumer run. A green coverage percentage is supplemental evidence, not the goal.

## Next Agent Prompt

Implementation and verification are complete on `fix/audit-gates`, based on
`3f89316`. Review [PR #3](https://github.com/nekomario28/gxkit/pull/3); do not extend
the scope, add tools or create a release. Preserve the repaired gates and their
mutation proofs. Main is unchanged until the PR is merged.

Status: all four goals verified. Baseline v1 is rejected; users explicitly
recreate accepted debt using `--write-baseline` (no migration).

- [x] [1. Shared gates](slices/01-gates.md): A01, A02, A03.
- [x] [2. Strict inputs and boundaries](slices/02-inputs.md): A04–A09, A11.
- [x] [3. Behavioral guards](slices/03-guards.md): A10 and mutation proofs.
- [x] [4. Consumer and CI verification](slices/04-verification.md).

## Ownership and contracts

- `gxcore.loading` owns invocation-scoped module reuse and strict member
  conversion. Domain loaders declare their formats; they do not filter failures.
- `gxcore.baseline` owns multiplicity-preserving comparison. Domain checks own
  stable relationship identity; numeric prose and image coordinates are not IDs.
- `gxkit` owns routing, not another inspection lifecycle. Every import stage
  reports an artifact-initiated exit as input failure (exit 2), never success.
- Accepted input representations produce equivalent models. Empty declarations,
  zero intervals, missing members and non-finite numbers are explicit cases.
- Gate tests inspect executable commands, not strings left in comments. Mutation
  drills must demonstrate rejection and restore every temporary change.

## Non-goals

No seventeenth tool, graph-tool merger, runtime reproducibility claim, history
rewrite, new infrastructure, renderer redesign, automatic baseline migration or
PyPI publication. No user token is needed for this work. Package patches may be
bumped where changed code requires a new shared-core helper.

## Evidence ledger

Baseline: audit reproductions confirmed on `3f89316`; existing suite passes 1325
cases with 100% coverage despite the defects. The supported Git/uvx install path
works; index-only resolution before PyPI publication is not the consumer contract.

Shared gate checkpoint: exit/directory test red in all three exit variants,
execution-counter test red (2 vs 1), duplicate-occurrence test red, and replaced
partner baseline test red; each now green. Same-size/source-edit regression also
went red before bypassing bytecode. Existing suite: 1335 pass; lint/types pass.

Input checkpoint: five public-CLI member tests went red, then green after
strict conversion. Boundary regressions exposed tuple-default, empty-interval,
non-finite-time, fractional/boolean/string seed and API path-boundary defects;
now green. Empty-set reference regressions will also be mutation-proven before
closeout. Strict local gate: 100% statements; lint/types/security checks pass.

Guard checkpoint: green controls followed by named rejected mutants,
including all original audit fault classes, commented/echoed/disabled coverage
commands and both empty-set reference cases. Mutation drilling exposed a missing
`--no-cov` rejection, repaired and retested. Additional introspection-stage
SystemExit variants went red before extending the routing exception boundary.
Independent final review reproduced inherited future flags in the source loader;
the annotation regression went red before disabling inheritance. The added
mutation pins this execution-semantics boundary too.

Verification snapshot at `4d1868f7477b1ad3d195c442eefc96fcad257820`:
strict full local gates pass (1393 tests, 100% statements, 28 rejected mutants,
strict types/lint/security and all wheel/sdist validations). Isolated tool/cache
installs from local Git and public Git both verify that exact SHA and pass the
consumer exit/baseline scenarios. [PR CI](https://github.com/nekomario28/gxkit/actions/runs/38609898548)
passes every job, including Windows/macOS, the Ubuntu Python matrix, mutation
proofs and the isolated Git consumer. Independent review's two findings were
reproduced, repaired and guarded. No reviewer-suite success is claimed: its
read-only sandbox lacked a writable temporary directory.

No visual redesign or exhaustive all-domain correctness proof is claimed. The
seed skill's declaration/runtime boundary is clarified; clean-context skill-model
evaluation is NOT RUN. Publication/release and merge remain separate actions.

Full logs belong outside the repository. Decisions belong in [choices](choices.md).
