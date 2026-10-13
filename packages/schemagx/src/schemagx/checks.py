"""schemagx's domain knowledge: is this schema sound?

The same graph questions as any model: are there dangling references, a cycle
that needs deferred constraints, and tables nothing points at. Cycles come from
`gxcore.graph.find_cycle`.
"""

from __future__ import annotations

from gxcore import ERROR, INFO, WARN, Problem, Report
from gxcore.graph import reverse

from .model import Schema
from .render import compute_layout, node_box


def inspect_schema(schema: Schema, name: str | None = None) -> Report:
    name = name or schema.name
    declared = set(schema.table_names())
    edges = schema.edges()

    report = Report(
        name=name,
        subject=f"schema: {len(schema.tables)} tables, {len(schema.foreign_keys)} foreign keys",
        details=[f"{len(schema.tables)} tables, {len(schema.foreign_keys)} foreign keys",
                 "roots: " + (", ".join(schema.roots) or "none")],
    )
    out: list[Problem] = []

    for child, parent in schema.foreign_keys:
        ct, cc = schema.split(child)
        pt, pc = schema.split(parent)
        if ct not in declared:
            out.append(Problem(ERROR, "dangling-foreign-key",
                               f"{child!r} references unknown table {ct!r}"))
        elif cc not in schema.tables[ct]:
            out.append(Problem(ERROR, "dangling-foreign-key",
                               f"{child!r} references unknown column {cc!r}", target=ct))
        if pt not in declared:
            out.append(Problem(ERROR, "dangling-foreign-key",
                               f"{parent!r} references unknown table {pt!r}"))
            continue
        if pc not in schema.tables[pt]:
            out.append(Problem(ERROR, "dangling-foreign-key",
                               f"{parent!r} references unknown column {pc!r}", target=pt))
            continue

        child_type, parent_type = schema.type_of(child), schema.type_of(parent)
        if child_type and parent_type and child_type != parent_type:
            out.append(Problem(WARN, "fk-type-mismatch",
                               f"{child} is {child_type!r} but {parent} is {parent_type!r}",
                               target=pt))

        pk = schema.primary_keys.get(pt)
        if pk and pc != pk:
            out.append(Problem(WARN, "fk-to-non-primary-key",
                               f"{child} references {parent}, which is not {pt}'s primary key "
                               f"({pk})", target=pt))

    cycle = schema.cycle()
    if cycle:
        out.append(Problem(WARN, "cyclic-foreign-key",
                           f"foreign-key cycle: {' → '.join(cycle)} — inserts need deferred "
                           "constraints", target=cycle[0]))

    for table in schema.table_names():
        if table not in schema.primary_keys:
            out.append(Problem(INFO, "missing-primary-key",
                               f"table {table!r} has no primary key", target=table))

    reverse_edges = reverse(edges)
    for table in schema.table_names():
        if table in schema.roots:
            continue
        # A leaf that references a parent is not an orphan; a table nothing
        # points at and that points at nothing is dead weight.
        if not reverse_edges.get(table) and not edges.get(table):
            out.append(Problem(INFO, "orphan-table",
                               f"nothing references {table!r} and it references nothing",
                               target=table))

    if not schema.tables:
        out.append(Problem(INFO, "no-tables", "the schema declares no tables"))

    positions, r = compute_layout(schema)
    for p in out:
        if p.bbox is None and p.target in positions:
            p.bbox = node_box(positions[p.target], r)

    report.problems = out
    return report
