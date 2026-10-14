---
name: seedgx
description: Use when an agent has written a run whose randomness must be reproducible and declared a seed manifest (one seed per stream) — check for a stream with no seed, a seed outside the 32-bit range, two streams sharing a seed, a duplicate stream, or a manifest marked non-deterministic. Provides `seedgx inspect` with stable codes, an exit code, `--json` and a storyboard. Part of the gxkit family.
---

# seedgx

`seedgx` reads a random-seed manifest written as data and reports what would make
the run non-reproducible, before it runs.

## Use it

```sh
uv tool install "git+https://github.com/nekomario28/gxkit#subdirectory=packages/seedgx"
seedgx inspect seed.py            # report + storyboard; exit 1 on any error
seedgx inspect seed.py --json
seedgx render  seed.py -o seed.png
```

Write the manifest as a Python file:

```python
import seedgx as s

spec = s.SeedSpec(
    streams=[s.Stream("python", 42), s.Stream("numpy", 7)],
    deterministic=True,
)
```

Or module-level `STREAMS` (a list of `(name, seed)` pairs) / `DETERMINISTIC` /
`NAME`.

## What it catches

| code | severity | what it means |
| --- | --- | --- |
| `missing-seed` | error | a stream with no seed |
| `seed-out-of-range` | error | a seed outside `0..2**32-1` |
| `duplicate-stream` | error | the same stream name declared twice |
| `duplicate-seed` | warn | two streams share a seed (correlated randomness) |
| `non-deterministic` | info | the manifest is marked non-deterministic |
| `no-streams` | info | the manifest declares no streams |

## Why the checks can be trusted

Every check has a test that builds the defect and asserts it fires, and one that
asserts an honest manifest stays quiet (`packages/seedgx/tests/`).

## Where it fits

Part of `gxkit`; the `inspect` contract (stable codes, exit codes, `--json`, a
storyboard) is shared. See the family skill at the repository root.
