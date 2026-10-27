# Releasing

The packages are built with `uv build` and published to PyPI with `uv publish`.
Publishing needs a PyPI API token; it is the one step that must be run by the
owner.

## When it is ready to publish

"Another review found something" is not a reason to hold a release; it is the
normal state of software, and the useful question is whether what it found was
*inside the published promise* or beside it. The gate is therefore:

1. **No known defect is unfixed.** Every finding so far carries a guard (a test, a
   mutation, a generated ratchet), so the same class cannot come back unnoticed.
2. **The promise has not moved.** `docs/CONTRACT.md` is the promise, and during the
   work that produced this release it was *created* and then only added to: over
   the period, 13 codes were added, **0 removed**, and **0 severities moved**. The
   contract allows exactly that — "which codes a tool can emit … the set grows" —
   and a baseline absorbs a new finding. A change to an exit code, a JSON key, a CLI
   flag or a model field name would be a different matter and would need the
   document updated first.
3. **The promise is checked, not asserted.** `packages/gxkit/tests/test_contract_conformance.py`
   drives the *installed console scripts* and falsifies each Stable sentence: the
   three exit codes, the report's keys, the flags doing what they say, the umbrella's
   `tools`/`codes`/routing, the baseline forgiving an old error and failing a new
   one, every tool reading a Python file and the three document readers reading
   their own document. Each test names the sentence it holds.
4. **What is not promised is written down.** The boundaries live in that document's
   "Not stable" section, `docs/SEMANTICS.md` (what each claim was measured against),
   `docs/IDENTITY.md` (the sites a finding is identified by) and
   `docs/SKILL-EVAL.md` (what the skill evaluation does not cover).

A first release has an advantage worth naming: nobody depends on it yet, so a
correction that *adds* a finding — the shape every fix in this work took — cannot
break a consumer. After 1.0.0, the same corrections ship as patch or minor
releases, and the baseline is what lets a user take them without a red build.

## What has been verified without a token

The publish step is the one part no test can complete here, so it was measured as
far as it goes:

- **`uv publish --dry-run` over the built `dist/`** parses every file's metadata the
  way an upload would. It is part of `scripts/check.sh --full`.
- **A whole publish against a local index**: with a placeholder token and a server
  accepting uploads on `127.0.0.1`, `uv publish --publish-url … dist/*.whl
  dist/*.tar.gz` exits 0 and sends **36 POSTs**, one per file. That exercises the
  command, the file list, the multipart upload and the credential plumbing end to
  end.
- **An install from a local PEP 503 index** of the umbrella and of each of the 16
  tools in its own environment (`scripts/check_publish.py`), which is the same index
  layout PyPI serves.

What is *not* verified, and cannot be from here: that PyPI accepts the token, and
that the names are still free at upload time (all 18 were free on 2026-10-15). If a
name has been taken by then, the upload for that package fails and nothing else is
affected; publish dependency-first so a failure leaves the rest untouched.

## Build and check

```sh
uv build --all-packages -o dist
uvx twine check dist/*
```

`scripts/check.sh --full` does both. To see the publish order — `gxcore` first,
the tools, then `gxkit-cli` last — run `uv run python scripts/release.py`; to
validate a built `dist/` against the `pyproject` files, run
`uv run python scripts/release.py --check dist`.

Every wheel must carry its `LICENSE` and declare `License-Expression: MIT` (see
[`LICENSING.md`](LICENSING.md)); `scripts/prepublish_check.py` guards the repo
side.

## Version scheme

The first publication carries **1.0.0 for every package**, and each consumer
requires `gxcore>=1.0,<2.0`. `docs/CONTRACT.md` publishes what 1.0.0 promises —
codes, severities, exit codes, the JSON keys, the baseline format, the CLI shape
and the supported Pythons — so a 0.x publication would contradict the document.
The repository tag is `v1.0.0`; package versions and the tag are separate numbers
and stay separate.

All eighteen names were free on PyPI when this was written (checked with the
command below). Nothing has been published, so no version is an increment from a
released one.

## The release, in order

Everything is verified by the time this runs; the two steps that need the owner
are the token and the decision to publish.

```sh
# 1. Everything must be green on the commit you are about to release.
scripts/check.sh --full          # suite, coverage, 61 mutants, distributions,
                                 # the local-index install gate
uv run python scripts/check_consumer.py \
    --repository https://github.com/nekomario28/gxkit --revision "$(git rev-parse HEAD)"

# 2. Build what will be uploaded, and prove it resolves from an index.
rm -rf dist && uv build --all-packages -o dist
uvx twine check dist/*
uv run python scripts/release.py --check dist
uv run python scripts/check_publish.py --skip-build

# 3. Publish, dependency order: gxcore first, then the tools, then the umbrella.
#    The token is the owner's; it is the only step that cannot be automated here.
export UV_PUBLISH_TOKEN=pypi-...
uv publish dist/*.whl dist/*.tar.gz

# 4. Tag and release, using the CHANGELOG entry as the release body.
git tag -a v1.0.0 -m "gxkit v1.0.0 — first release"
git push origin v1.0.0
gh release create v1.0.0 --title "gxkit v1.0.0 — first release" \
    --notes-file <(sed -n '/^## \[1.0.0\]/,/^## \[0.9.1\]/p' CHANGELOG.md | head -n -1)
```

The release body is extracted from `CHANGELOG.md` rather than written twice, so
the two cannot disagree. The `v1.0.0` link in the CHANGELOG resolves once step 4
creates the tag.

`uv publish` takes the whole `dist/` in one call and uploads in the order given;
the tools pin `gxcore>=1.0,<2.0`, so a published tool never resolves an unrelated
`gxcore`. If a single package must be published on its own, `scripts/release.py`
prints the order to use.

> **The name `gxkit` is taken on PyPI** (an unrelated package), so the umbrella
> is distributed as **`gxkit-cli`**. The import package stays `gxkit` and the
> command stays `gxkit`.

## Prove the index before publishing

The Git route installs from a checkout, so it cannot catch a dependency range
only an index resolver would reject. `scripts/check_publish.py` builds every
distribution, serves them from a local PEP 503 index, and installs the umbrella
against that index alone — the same resolution a PyPI install performs, with
nothing published. It runs in `scripts/check.sh --full` and in the packaging CI
job.

```sh
uv run python scripts/check_publish.py          # build, then install from the index
uv run python scripts/check_publish.py --skip-build   # reuse an existing dist/
```

Third-party dependencies (Pillow, matplotlib, moderngl, numpy) resolve from
PyPI; the family's own packages resolve only from the local index.

## Check the names

```sh
for p in gxcore chartgx levelgx flowgx protogx authzgx depsgx schemagx docgx shadergx framegx apigx netgx envgx pipegx seedgx crongx checkgx gxkit-cli; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://pypi.org/pypi/$p/json")
  echo "$p -> $code (404 = free)"
done
```

All eighteen returned `404` (free) on 2026-10-15, so no name needs to be
claimed first.

## Before the first release, and until it happens

Install straight from the repository — the README documents the single-tool form:

```sh
uv tool install "git+https://github.com/nekomario28/gxkit#subdirectory=packages/chartgx"
chartgx inspect my_chart.py
```

`uvx <tool> …` and `gxkit …` (the umbrella) only work once the distributions are
published; the README says so and `scripts/check_consumer.py` executes the
documented form so it cannot rot.

## Tags and the action

Cut a tag (`vX.Y.Z`) and a GitHub release; the reusable action uses the repo
itself, so a caller pins it with `uses: nekomario28/gxkit@vX.Y.Z`.
