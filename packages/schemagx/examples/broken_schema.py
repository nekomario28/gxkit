"""A schema with several faults.

  * posts.author_id is text but users.id is int      -> fk-type-mismatch
  * legacy.owner -> ghost.id names an unknown table  -> dangling-foreign-key
  * posts.draft_id / tags.missing are unknown columns -> dangling-foreign-key
  * posts <-> tags is a foreign-key cycle            -> cyclic-foreign-key
  * tags / legacy / notes have no primary key        -> missing-primary-key
  * notes is referenced by nobody and references nobody -> orphan-table
"""

import schemagx as s

NAME = "Tangled schema"

schema = s.Schema(
    tables={
        "users": {"id": "int", "email": "text", "manager_id": "int"},
        "posts": {"id": "int", "author_id": "text", "approver_id": "int"},
        "tags": {"id": "int", "post_id": "int"},
        "legacy": {"id": "int"},
        "notes": {"id": "int"},
    },
    primary_keys={"users": "id", "posts": "id"},
    foreign_keys=[
        ("posts.author_id", "users.id"),    # type mismatch (text vs int)
        ("posts.approver_id", "tags.id"),
        ("tags.post_id", "posts.id"),       # cycle posts <-> tags
        ("users.manager_id", "users.id"),   # self-reference is fine
        ("legacy.owner", "ghost.id"),       # unknown table
        ("posts.draft_id", "tags.id"),      # unknown column on posts
        ("tags.missing", "users.id"),       # unknown column on tags
    ],
    roots=["users"],
)
