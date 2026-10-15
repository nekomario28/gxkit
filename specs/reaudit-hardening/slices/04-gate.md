# A coverage gate that can fail

Retire R04 and R05. The guard observes the environment its stub runs in, not
only the argv it logs, so a `PYTEST_ADDOPTS` override cannot disable coverage
unnoticed. It then replays a failing coverage command and requires the script to
exit nonzero, so a swallowed failure cannot pass either.

Checkpoint: the unmodified tree is accepted, and the environment-disabled,
failure-swallowed and later mutants are each rejected by the named test.
