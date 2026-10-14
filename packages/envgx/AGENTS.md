# envgx, for AI agents

A person pointed you here. `envgx` checks that a configuration is coherent before
it ships: declare the variables and the names the code reads, then `envgx inspect`
finds a reference to something undeclared, a declaration nothing reads, a secret
with a default, a type that is not real, and a required variable that also has a
default — plus a storyboard.

This tool is part of `gxkit`; the review contract (`inspect`, `--json`, exit
codes, storyboard) is shared with every other tool in the family.

## Set it up

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/envgx" envgx --help
# or, from a clone:
uv tool install ./packages/envgx    # puts `envgx` on PATH
```

## The loop

1. **Write** the config as a `.py` file that builds an `Environment` (or defines
   `VARIABLES` / `REFERENCES` / `NAME`).
2. **Inspect** — `envgx inspect env.py`. Prints the summary, every problem with a
   stable `code`, and writes `<name>.storyboard.png`.
   **Exit code 1 means at least one error.**
3. **Fix** and inspect again; look at the storyboard if you can view images.
4. **Render** — `envgx render env.py -o env.png`.

## Reading the report

- `error` — `secret-with-default`, `unknown-type`, `duplicate-variable`,
  `empty-name`, `undeclared-reference`.
- `warn` — `required-with-default`.
- `info` — `unused-variable`, `no-variables`.

Common fixes: `undeclared-reference` → declare the name or remove the read;
`secret-with-default` → drop the default; `unused-variable` → remove it or read
it; `unknown-type` → use `str`/`int`/`float`/`bool`. Use `--json` to branch on the
result.
