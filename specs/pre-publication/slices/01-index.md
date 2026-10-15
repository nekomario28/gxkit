# 01-index

Prove resolution from an index
Build every distribution, serve them from a local PEP 503 index, and install the
umbrella against that index alone with workspace sources disabled. Verify the
revision, the versions, that every tool routes, and that a clean and a faulty
artifact still produce the documented exit codes. Third-party dependencies may
come from PyPI; the family's own packages may not.

Checkpoint: omitting a wheel, or corrupting one package's gxcore range, makes
the gate red.
