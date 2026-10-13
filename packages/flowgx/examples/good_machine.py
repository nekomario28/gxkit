"""A review workflow that should pass.

Every state is reachable from the start, and every state can still reach an
accepting state. The review <-> changes loop is a cycle, reported as a note.
"""

import flowgx as f

NAME = "Review workflow"

machine = f.Machine(
    states=["draft", "review", "changes", "published", "archived"],
    start="draft",
    accept=["published", "archived"],
    transitions=[
        ("draft", "review", "submit"),
        ("review", "published", "approve"),
        ("review", "changes", "request"),
        ("changes", "review", "resubmit"),
        ("published", "archived", "archive"),
    ],
)
