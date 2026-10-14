# protogx, for AI agents

A person pointed you here. `protogx` checks that a protocol cannot deadlock or
lose a message before you implement it: declare states, transitions and the
messages that drive them as a Python file, then `protogx inspect` proves every
state is reachable, that a terminal is reachable from everywhere, and that no
declared message or awaited response is left unhandled — plus a storyboard.

This tool is part of `gxkit`; the review contract (`inspect`, `--json`, exit
codes, storyboard) is shared with every other tool in the family.

## Set it up

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/protogx" protogx --help
# or, from a clone:
uv tool install ./packages/protogx    # puts `protogx` on PATH
```

## The loop

1. **Write** the protocol as a `.py` file that builds a `Protocol` (or defines
   `STATES` / `TRANSITIONS` / `START` / `TERMINAL` / `MESSAGES` / `REQUESTS` /
   `RESPONSES`).
2. **Inspect** — `protogx inspect proto.py`. Prints the state summary, every
   problem with a stable `code`, and writes `<name>.storyboard.png`.
   **Exit code 1 means at least one error.**
3. **Fix** the `error` and `warn` problems, inspect again. Look at the storyboard
   if you can view images — each numbered box proves a problem.
4. **Render** — `protogx render proto.py -o proto.png`.

## Reading the report

- `error` — `no-start`, `unknown-state`, `unknown-message`, `unhandled-message`
  (a declared message nothing handles), `nondeterministic` (one state handles a
  message two ways), `deadlock` (no way out), `no-exit` (cannot reach a
  terminal), `unreachable-state`, `no-terminal`.
- `warn` — `missing-response` (an awaited reply nothing sends).
- `info` — `cycle` (a note, not necessarily wrong).

Common fixes: `unhandled-message` → add the transition or drop the message;
`nondeterministic` → split on the message; `deadlock` / `no-exit` → add a path to
a terminal; `unreachable-state` → wire it in or remove it. Use `--json` to branch
on the result.
