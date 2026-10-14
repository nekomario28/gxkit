# Releasing

The packages are built with `uv build` and published to PyPI with `uv publish`.
Publishing needs a PyPI API token; it is the one step that must be run by the
owner.

## Build and check

```sh
uv build --all-packages -o dist
uvx twine check dist/*
```

Every wheel must carry its `LICENSE` and declare `License-Expression: MIT` (see
[`LICENSING.md`](LICENSING.md)); `scripts/prepublish_check.py` guards the repo
side.

## Publish

Once the names are claimed on PyPI and a token is available:

```sh
export UV_PUBLISH_TOKEN=pypi-...          # or: uv publish --token pypi-...
uv publish dist/*.whl dist/*.tar.gz
```

Publish **`gxcore` first** (the tools depend on it), then the tools, then the
`gxkit-cli` umbrella. The tools already pin it (`gxcore>=0.4,<0.5`) so a
published tool does not resolve an unrelated `gxcore`.

> **The name `gxkit` is taken on PyPI** (an unrelated package), so the umbrella
> is distributed as **`gxkit-cli`**. The import package stays `gxkit` and the
> command stays `gxkit`.

## Check the names

```sh
for p in gxcore chartgx levelgx flowgx protogx authzgx depsgx schemagx docgx shadergx framegx gxkit-cli; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://pypi.org/pypi/$p/json")
  echo "$p -> $code (404 = free)"
done
```

Until then, install straight from the repository:

```sh
uvx --from "git+https://github.com/nekomario28/gxkit#subdirectory=packages/gxkit" gxkit tools
```

## Tags and the action

Cut a tag (`vX.Y.Z`) and a GitHub release; the reusable action uses the repo
itself, so a caller pins it with `uses: nekomario28/gxkit@vX.Y.Z`.
