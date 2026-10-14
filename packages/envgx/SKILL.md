---
name: envgx
description: Use when an agent has written an environment / configuration declaration (variables plus the names the code reads) and must check it before shipping — a reference to an undeclared name, a declaration nothing reads, a secret with a default, an unknown type, a required variable that also has a default. Provides `envgx inspect` with stable codes, an exit code, `--json` and a storyboard. Part of the gxkit family.
---

# envgx

`envgx` reads a configuration written as data and reports what is wrong before it
ships: the drift between what the code reads and what is declared, plus the
safety faults (a secret in source).

## Use it

```sh
uv tool install "git+https://github.com/nekomario28/gxkit#subdirectory=packages/envgx"
envgx inspect env.py            # report + storyboard; exit 1 on any error
envgx inspect env.py --json
envgx render  env.py -o env.png
```

Write the config as a Python file:

```python
import envgx as e

env = e.Environment(
    variables=[
        e.Variable("DATABASE_URL", required=True, secret=True),
        e.Variable("PORT", type="int", default="8080"),
    ],
    references=["DATABASE_URL", "PORT"],
)
```

Or module-level `VARIABLES` (a name → spec mapping) / `REFERENCES` / `NAME`.

## What it catches

| code | severity | what it means |
| --- | --- | --- |
| `secret-with-default` | error | a secret with a default (the secret is in source) |
| `unknown-type` | error | a type that is not `str` / `int` / `float` / `bool` |
| `duplicate-variable` | error | the same name declared twice |
| `empty-name` | error | a variable with an empty name |
| `undeclared-reference` | error | the code reads a name that is not declared |
| `required-with-default` | warn | required and has a default — pick one |
| `unused-variable` | info | declared but never read |
| `no-variables` | info | the environment declares no variables |

## Why the checks can be trusted

Every check has a test that builds the defect and asserts it fires, and one that
asserts an honest config stays quiet (`packages/envgx/tests/`).

## Where it fits

Part of `gxkit`; the `inspect` contract (stable codes, exit codes, `--json`, a
storyboard) is shared. See the family skill at the repository root.
