---
name: checkgx
description: Inspect a check registry for checks that cannot fail — a name written twice, a check sitting in the report's metadata, a declared check nothing evaluates, an evaluated name nobody declares. Use when a test suite, probe or verifier has checks that read as coverage, or after merging work that appended checks from several branches.
---

# checkgx

A registry is the list of checks an artifact declares and the runner reads. When those two sets differ, or
when a name is written twice, the result still looks green: a mapping keeps one copy, metadata is never
evaluated, and a typo on either side drops a gate without a word.

## Use it

```python
import checkgx as c

CHECKS = c.Registry(
    checks=["a_probe_passes", "strings_match"],   # as written; duplicates kept on purpose
    evaluated=["a_probe_passes", "strings_match"],# the union of what the runner reads
    metadata=["status", "note"],                  # beside the checks, never evaluated
)
```

```sh
checkgx inspect checks.py     # exit 1 on any error
```

## Codes

`duplicate-check`, `check-in-metadata`, `check-never-evaluated`, `evaluated-but-undeclared`, `no-checks`
are errors; `not-a-proof-of-failure` is a standing warning, and it is deliberate: a registry can be perfect
while a predicate inside it returns a constant. Run the suite against a broken build for that, and do not
read this tool's silence as soundness.
