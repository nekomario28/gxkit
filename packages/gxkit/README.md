# gxkit

**One entry point for the family.** An artifact goes in; the right `*gx` tool is
chosen and run. This is the executable form of the family skill's promise:
*detect the artifact, route it to the one tool per domain.*

```sh
gxkit tools              # what can be inspected
gxkit inspect chart.py   # detect the artifact and route
gxkit inspect levelgx level.py   # or name the tool explicitly
```

```
$ gxkit tools
authzgx    permission models
chartgx    matplotlib charts
depsgx     module dependency graphs
docgx      pages / slides
flowgx     state machines
framegx    rendered animations
levelgx    game levels
protogx    protocols
schemagx   relational schemas
shadergx   fragment shaders
```

## Detection

`gxkit inspect` loads the file and reads the object it defines — a `Machine`, a
`Level`, a `Schema`, a matplotlib `Figure`, … — then runs that tool's `inspect`
with the same flags (`--json`, `--no-storyboard`, `-o`). If it cannot tell, it
says which tools exist and exits 2; naming the tool explicitly always works.

The catalogue is static (`gxkit.registry`), so `tools` and detection never
import matplotlib or modernGL; a tool is imported only when it is chosen.

## Install

Installs every tool at once (the meta-package depends on all of them):

```sh
uv tool install "git+https://github.com/nekomario28/gxkit#subdirectory=packages/gxkit"
```

MIT licensed. See the [repository README](../../README.md).
