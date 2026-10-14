# Security

## Reporting

Report a vulnerability privately with GitHub's [security advisories](https://github.com/nekomario28/gxkit/security/advisories/new).
Please do not open a public issue for a security problem.

## Scope, and known boundaries

`inspect` reads an artifact by **importing and running the Python file** you give
it — that is by design and documented in the README. gxkit only inspects files
you trust; running it on an untrusted file is running an untrusted script.

Worth reporting:

- any path where `inspect` executes something *besides* the artifact file named;
- a way the reusable GitHub Action installs or runs code from a source other
  than the pinned repository;
- a misuse of a dependency (matplotlib, numpy, Pillow, modernGL, ffmpeg) that
  gxkit exposes.

Not a gxkit vulnerability:

- running `gxkit inspect` on a file you do not trust (see above);
- the artifact's own code doing something malicious.

## Running an untrusted artifact

`inspect` executes the artifact, so treat an untrusted artifact as an untrusted
program and give it an environment with nothing to steal:

- **No network** (the tools never need it), **no secrets** in the environment,
  and a **disposable** container or VM.
- Build an image that already has gxkit installed, then run only the artifact:

  ```dockerfile
  FROM python:3.12-slim
  RUN pip install "gxkit-cli @ git+https://github.com/nekomario28/gxkit#subdirectory=packages/gxkit"
  WORKDIR /w
  ENTRYPOINT ["gxkit", "inspect"]
  ```

  ```sh
  docker run --rm --network=none -v "$PWD:/w:ro" gxkit-inspect /w/artifact.py
  ```

The reusable GitHub Action runs on an ephemeral hosted runner. Pair it with
`permissions: contents: read` and a job that exposes no secrets; never run it on
an artifact you would not run as a script on that runner.

## Supported versions

The **latest release** of every distribution: `gxcore`, each `*gx` tool, and the
`gxkit-cli` umbrella. Only the latest minor line of each is supported; older tags
are not. Python **3.10–3.13**.
