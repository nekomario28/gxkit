# seedgx, for AI agents

A person pointed you here. `seedgx` checks seed declarations, not actual runtime
reproducibility: declare one seed per stream, then `seedgx inspect` finds a stream
with no seed, a seed outside the 32-bit range, a duplicate stream, a seed shared
between two streams, and a manifest marked non-deterministic — plus a storyboard.

This tool is part of `gxkit`; the review contract (`inspect`, `--json`, exit
codes, storyboard) is shared with every other tool in the family.

## Set it up

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/seedgx" seedgx --help
# or, from a clone:
uv tool install ./packages/seedgx    # puts `seedgx` on PATH
```

## The loop

1. **Write** the manifest as a `.py` file that builds a `SeedSpec` (or defines
   `STREAMS` / `DETERMINISTIC` / `NAME`).
2. **Inspect** — `seedgx inspect seed.py`. Prints the summary, every problem with
   a stable `code`, and writes `<name>.storyboard.png`.
   **Exit code 1 means at least one error.**
3. **Fix** and inspect again; look at the storyboard if you can view images.
4. **Render** — `seedgx render seed.py -o seed.png`.

## Reading the report

- `error` — `missing-seed`, `invalid-seed`, `seed-out-of-range`, `duplicate-stream`.
- `warn` — `duplicate-seed`.
- `info` — `non-deterministic`, `no-streams`.

Common fixes: `missing-seed` → give it a seed; `duplicate-seed` → change one;
`seed-out-of-range` → use a value in `0..2**32-1`; `duplicate-stream` → merge
them. Use `--json` to branch on the result.
