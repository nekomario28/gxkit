# Inspection correctness hardening

## Goal

Fix the eleven reproduced v0.9.1 audit findings before adding another domain.
Every regression must fail on the audited revision and pass after its repair.
Finish with strict local gates, independent review, remote CI, and an isolated
consumer run. A green coverage percentage is supplemental evidence, not the goal.

## Next Agent Prompt

You are implementing this hardening plan on `fix/audit-gates`, based on `3f89316`.
Resume at [strict inputs](slices/02-inputs.md), then proceed through the checklist
without stopping at intermediate commits. Update this prompt and the evidence
ledger after each checkpoint. Do not add tools or release tags. Preserve clean
inputs, stable existing codes, optional storyboards and the 100% statement floor.

Status: shared gates implemented and focused regressions pass. No blockers. Baseline v1 will be rejected;
users explicitly recreate accepted debt using `--write-baseline` (no migration).

- [x] [1. Shared gates](slices/01-gates.md): A01, A02, A03.
- [ ] [2. Strict inputs and boundaries](slices/02-inputs.md): A04–A09, A11.
- [ ] [3. Behavioral guards](slices/03-guards.md): A10 and mutation proofs.
- [ ] [4. Consumer and CI verification](slices/04-verification.md).

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

Record named red/green regression results here, not full terminal transcripts.
Full logs belong outside the repository. Decisions belong in [choices](choices.md).
