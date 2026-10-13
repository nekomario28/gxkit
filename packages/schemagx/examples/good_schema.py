"""A blog schema that should pass: references resolve, no cycles, no dead tables."""

import schemagx as s

NAME = "Blog schema"

schema = s.Schema(
    tables={
        "users": {"id": "int", "email": "text"},
        "posts": {"id": "int", "author_id": "int", "title": "text"},
        "comments": {"id": "int", "post_id": "int", "body": "text"},
    },
    primary_keys={"users": "id", "posts": "id", "comments": "id"},
    foreign_keys=[
        ("posts.author_id", "users.id"),
        ("comments.post_id", "posts.id"),
    ],
    roots=["users"],
)
