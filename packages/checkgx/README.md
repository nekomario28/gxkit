# checkgx

**Inspect a check registry for checks that cannot fail.** Declare the checks an
artifact writes, the ones its runner actually evaluates, and the keys that sit
beside them as metadata; `checkgx inspect` names duplicates, checks nothing reads,
names read but never declared, and checks that landed among the metadata.

One of the [`gxkit`](../../README.md) tools, built on [`gxcore`](../gxcore).

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/checkgx" checkgx inspect checks.py
# local:  uvx --from ../../packages/checkgx checkgx inspect checks.py
```

## Why this exists

Three ways a check reads as coverage and cannot fail, all met in one afternoon of
measuring a product:

- **a name written twice**: a mapping keeps one of them, so the others never run;
- **a check in the report's metadata**: it compiles, the run prints PASS, and the
  dict the runner reads never contained it;
- **a name on one side of the declared/evaluated line only**: a typo in the
  declaration silently drops a gate.

Each of them looks like a green result. That is the property this tool is for.

## Writing a registry

```python
import checkgx as c

registry = c.Registry(
    checks=["a_probe_passes", "strings_match", "strings_match"],  # as written, duplicates kept
    evaluated=["a_probe_passes", "strings_match"],  # what the runner reads
    metadata=["status", "note"],  # never evaluated
)
```

## The contract

```
$ checkgx inspect broken_registry.py
broken_registry.py: checks
checks: 4 declared, 3 evaluated
  4 declared
  3 evaluated
  2 metadata keys
inspect: 4 problems (4 errors)
  [1] error -          duplicate-check: strings_match is written 2 times; a mapping keeps one of them and the rest are never run
  [2] error -          check-in-metadata: status sits among the report's metadata, which the runner never evaluates
  [3] error -          check-never-evaluated: output_nonempty is declared but no evaluated mapping names it
  [4] error -          evaluated-but-undeclared: stdout_is_json is evaluated but never declared; a typo here silently drops a gate
```

`examples/broken_registry.py` is that registry, and every one of the four is a
way a suite reports green while a gate is missing.

- **Exit code 1** when any `error`-severity problem is found.
- `--json` prints the same report machine-readably; `--no-storyboard` skips the
  image; `-o name.png` names it.

## Codes

| code | severity | meaning |
| --- | --- | --- |
| `duplicate-check` | error | a name is written more than once; one survives |
| `check-in-metadata` | error | a check name sits in a mapping the runner does not evaluate |
| `check-never-evaluated` | error | declared, and nothing evaluates it |
| `evaluated-but-undeclared` | error | evaluated, and no declaration provides it |
| `no-checks` | error | the registry declares nothing |
| `not-a-proof-of-failure` | warn | standing note: this reads the registry, not the predicates |

The last one is deliberate. A registry can be perfect while a predicate inside it
returns a constant; that needs the predicate, and saying so is better than
implying the check is thereby sound.

## What it inspects, and what it does not

It inspects the **registry**: the names, where they are written, and where they are
read. It does not run anything, does not import the artifact, and cannot tell you
whether a check's body can fail. For that, run the suite against a deliberately
broken build - which is what the `not-a-proof-of-failure` note points at.
