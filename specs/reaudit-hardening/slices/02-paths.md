# Invocation input identities

Retire R02. Resolve every requested input once, before any artifact executes,
and route, load and report from those identities. The human report keeps the
name a person typed; the load identity must be absolute so an artifact's own
cwd change cannot select another file.

Checkpoint: a relative artifact that chdirs onto a same-named clean file still
reports its own finding, and detection plus inspection still execute once.
