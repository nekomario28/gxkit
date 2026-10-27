# checkgx — working rules

- `checkgx inspect <file>` prints the report and writes a storyboard; **exit code 1** on any error.
- The model is **data**, not code: `Registry(checks=..., evaluated=..., metadata=...)`. Do not add a mode that
  imports and runs the artifact; running the checks is the suite's job, and this tool is about the registry.
- Every finding is an **error** except `not-a-proof-of-failure`, which is a warning because it is true of every
  registry this tool can ever see.
- New codes need a test that shows the shape being reported **and** a test that the clean shape is not.
- The storyboard is a diagram of declared → evaluated; keep it readable before keeping it pretty.
