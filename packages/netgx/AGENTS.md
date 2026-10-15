# netgx, for AI agents

A person pointed you here. `netgx` checks that a network topology is segmented
before it is built: declare nodes with a kind and the allowed traffic between
them, then `netgx inspect` finds an edge to an unknown node, a public entry that
reaches sensitive data, a self-loop, a duplicate edge, an isolated node, and a
topology with no public entry — plus a storyboard.

This tool is part of `gxkit`; the review contract (`inspect`, `--json`, exit
codes, storyboard) is shared with every other tool in the family.

## Set it up

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/netgx" netgx --help
# or, from a clone:
uv tool install ./packages/netgx    # puts `netgx` on PATH
```

## The loop

1. **Write** the topology as a `.py` file that builds a `Network` (or defines
   `NODES` / `EDGES` / `SENSITIVE`).
2. **Inspect** — `netgx inspect net.py`. Prints the summary, every problem with a
   stable `code`, and writes `<name>.storyboard.png`.
   **Exit code 1 means at least one error.**
3. **Fix** and inspect again; look at the storyboard if you can view images.
4. **Render** — `netgx render net.py -o net.png`.

## Reading the report

- `error` — `dangling-edge` (an edge to an unknown node),
  `public-reaches-sensitive` (a public node can reach sensitive data).
- `warn` — `self-loop`.
- `info` — `duplicate-edge`, `isolated-node`, `no-public`, `no-nodes` (the
  network declares nothing at all).

Common fixes: `dangling-edge` → fix the node name or declare it;
`public-reaches-sensitive` → remove the path or put a policy between;
`self-loop` → drop it; `isolated-node` → connect it or remove it. Use `--json` to
branch on the result.
