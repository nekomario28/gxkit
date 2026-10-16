"""A workflow with four structural faults, one per check.

  * ``rejected`` is declared but nothing transitions to it -> unreachable-state
  * ``limbo`` has no way out and is not accepting     -> dead-end
  * ``changes`` can never reach "published"           -> no-exit
  * ``review`` has two transitions on the event "act" -> ambiguous-transition

Uses the `STATES`/`TRANSITIONS` form of a level file.
"""

NAME = "Broken review workflow"

STATES = ["draft", "review", "changes", "published", "limbo", "rejected"]
START = "draft"
ACCEPT = ["published"]

TRANSITIONS = [
    ("draft", "review", "submit"),
    ("review", "published", "approve"),
    ("review", "changes", "act"),
    ("review", "published", "act"),
    ("changes", "limbo", "park"),
]
