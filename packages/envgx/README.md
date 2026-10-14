# envgx

**Inspect an environment / configuration declaration for drift.** Declare the
variables and the names the code reads; `envgx inspect` finds a reference to
something undeclared, a declaration nothing reads, a secret that carries a
default, a type that is not real, and a required variable that also has a default.

One of the [`gxkit`](../../README.md) tools, built on [`gxcore`](../gxcore).

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/envgx" envgx inspect env.py
# local:  uvx --from ../../packages/envgx envgx inspect env.py
```

## Writing a config

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

## The contract

```
$ envgx inspect broken_env.py
broken_env.py: Service config
env: 4 variables
storyboard: Service_config.storyboard.png
  4 variables
  2 references
inspect: 8 problems (4 errors)
  [1] error -          undeclared-reference: the code reads 'MISSING', which is not declared
  [2] error v[0]       secret-with-default: DATABASE_URL is secret but has a default — the secret would be in source
  [3] error v[1]       unknown-type: PORT has type 'integer'; use one of str, int, float, bool
  [4] error v[2]       duplicate-variable: PORT is declared more than once
  [5] warn  v[3]       required-with-default: DEBUG is required but also has a default — pick one
  [6] info  v[1]       unused-variable: PORT is declared but never read
  [7] info  v[2]       unused-variable: PORT is declared but never read
  [8] info  v[3]       unused-variable: DEBUG is declared but never read
```

- **Exit code 1** when any `error`-severity problem is found.
- `--json` prints the same report machine-readably; `--no-storyboard` skips the
  image; `-o name.png` names it.

## Checks

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

## Why it can be trusted

Every check is proven to fire on a config with the fault and to stay quiet on one
without (`tests/`). The drift checks are the same idea `schemagx` uses for keys.

MIT licensed.
