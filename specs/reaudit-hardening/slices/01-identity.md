# Stable network relationship identity

Retire R01. `dangling-edge` is a finding about a directed relationship, so its
identity must name the edge and the unknown endpoint. Occurrence multiplicity
already repairs repeated findings; it cannot distinguish two different
relationships that share a count.

Checkpoint: baseline write fails, a same-count replaced endpoint is reported as
a new error through the public CLI with JSON, and removing the identity makes
that regression red.
