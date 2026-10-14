# Hardening decisions

- **One load per invocation.** Use invocation-scoped module reuse in the existing
  loader, not a persistent cache or parallel tool-loading API. Subsequent calls
  must observe changed files. This keeps routing and inspection on the same
  generated artifact while retaining each tool's loader.
- **Baseline cutover.** Version 2 preserves repeated findings and explicit
  relationship IDs. Reject version 1 and ask for deliberate baseline recreation;
  guessing old relationship IDs could accept newly introduced debt.
- **Scope.** Repair existing inspectors and their guards; retain the shared core
  and thin domain tools. Do not add a tool, merge domains or manufacture a release.
