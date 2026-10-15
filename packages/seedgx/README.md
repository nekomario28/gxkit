# seedgx

**Inspect a random-seed manifest's declarations.** Declare one seed per
randomness stream; `seedgx inspect` finds a stream with no seed, a seed outside
the 32-bit range, two streams sharing a seed, a duplicate stream, and a manifest
marked non-deterministic.

One of the [`gxkit`](../../README.md) tools, built on [`gxcore`](../gxcore).

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/seedgx" seedgx inspect seed.py
# local:  uvx --from ../../packages/seedgx seedgx inspect seed.py
```

## Writing a manifest

```python
import seedgx as s

spec = s.SeedSpec(
    streams=[s.Stream("python", 42), s.Stream("numpy", 7)],
    deterministic=True,
)
```

Or module-level `STREAMS` (a list of `(name, seed)` pairs) / `DETERMINISTIC` /
`NAME`.

Seeds are integers in the unsigned 32-bit range, or `None` for a missing seed.
Floats, booleans and numeric strings are not coerced into integers. Malformed
members reject the artifact with their field/index (exit 2), never disappear.
This does not verify actual RNG initialization, algorithms, GPU execution or
runtime reproducibility. Equal seeds only imply matching sequences when the
RNG and initialization semantics also match.

## The contract

```
$ seedgx inspect broken_seed.py
broken_seed.py: Training
seed: 5 streams
storyboard: Training.storyboard.png
  5 streams
  not deterministic
inspect: 5 problems (3 errors)
  [1] error st[1]      missing-seed: stream 'numpy' has no seed — the run is not reproducible
  [2] error st[3]      duplicate-stream: stream 'torch' is declared more than once
  [3] error st[4]      seed-out-of-range: stream 'jax' has seed 4294967296, outside 0..4294967295
  [4] warn  st[2]      duplicate-seed: stream 'torch' reuses the seed of 'python' — matching RNGs may generate the same sequence
  [5] info  -          non-deterministic: the manifest is marked non-deterministic
```

- **Exit code 1** when any `error`-severity problem is found.
- `--json` prints the same report machine-readably; `--no-storyboard` skips the
  image; `-o name.png` names it.

## Checks

| code | severity | what it means |
| --- | --- | --- |
| `missing-seed` | error | a stream with no seed |
| `seed-out-of-range` | error | a seed outside `0..2**32-1` |
| `invalid-seed` | error | a seed is not an integer (booleans are not seeds) |
| `duplicate-stream` | error | the same stream name declared twice |
| `duplicate-seed` | warn | two streams share a seed; matching RNGs may repeat |
| `non-deterministic` | info | the manifest is marked non-deterministic |
| `no-streams` | info | the manifest declares no streams |

## Why it can be trusted

Every check is proven to fire on a manifest with the fault and to stay quiet on
one without (`tests/`).

MIT licensed.
