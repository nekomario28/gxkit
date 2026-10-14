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

## Supported versions

The latest release of each package.
