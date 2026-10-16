"""schemagx's domain knowledge: is this schema sound?

The same graph questions as any model: are there dangling references, a cycle
that needs deferred constraints, and tables nothing points at. Cycles come from
`gxcore.graph.find_cycle`.
"""

from __future__ import annotations

from gxcore import ERROR, INFO, WARN, Problem, Report
from gxcore.graph import cycle_witnesses, reverse, strongly_connected_components, topological_sort

from .model import Schema, type_family
from .render import compute_layout, node_box


def inspect_schema(schema: Schema, name: str | None = None) -> Report:
    name = name or schema.name
    declared = set(schema.table_names())
    edges = schema.edges()

    report = Report(
        name=name,
        subject=f"schema: {len(schema.tables)} tables, {len(schema.foreign_keys)} foreign keys",
        details=[
            f"{len(schema.tables)} tables, {len(schema.foreign_keys)} foreign keys",
            "roots: " + (", ".join(schema.roots) or "none"),
        ],
    )
    order = topological_sort(edges)
    if order is not None and len(order) > 1:
        report.details.append("create order: " + " → ".join(reversed(order)))
    cyclic = [c for c in strongly_connected_components(edges) if len(c) > 1]
    if cyclic:
        report.details.append(
            "cyclic tables: " + " | ".join("{" + ", ".join(sorted(c)) + "}" for c in cyclic)
        )
    out: list[Problem] = []

    for table, kinds in schema.not_modelled:
        # Not a fault: a limitation of what the model carries, said out loud.
        out.append(
            Problem(
                INFO,
                "not-modelled",
                f"{table}: the model does not carry the {kinds} clause(s) — found, not "
                "read into the model; reference integrity was still checked",
                target=table,
            )
        )

    # A declared name this tool consumes must resolve: a typo'd root would change
    # what the schema's roots are without saying so.
    for table in schema.roots:
        if table not in declared:
            out.append(
                Problem(
                    ERROR,
                    "dangling-reference",
                    f"`roots` names {table!r}, which is not a declared table",
                    identity=("dangling-reference", "roots", table),
                )
            )

    for child, parent in schema.foreign_keys:
        ct, cc = schema.split(child)
        pt, pc = schema.split(parent)
        if ct not in declared:
            out.append(
                Problem(
                    ERROR,
                    "dangling-foreign-key",
                    f"{child!r} references unknown table {ct!r}",
                    identity=(child, parent, "table", ct),
                )
            )
        elif cc not in schema.tables[ct]:
            out.append(
                Problem(
                    ERROR,
                    "dangling-foreign-key",
                    f"{child!r} references unknown column {cc!r}",
                    target=ct,
                    identity=(child, parent, "column", cc),
                )
            )
        if pt not in declared:
            out.append(
                Problem(
                    ERROR,
                    "dangling-foreign-key",
                    f"{parent!r} references unknown table {pt!r}",
                    identity=(child, parent, "parent-table", pt),
                )
            )
            continue
        if pc not in schema.tables[pt]:
            out.append(
                Problem(
                    ERROR,
                    "dangling-foreign-key",
                    f"{parent!r} references unknown column {pc!r}",
                    target=pt,
                    identity=(child, parent, "parent-column", pc),
                )
            )
            continue

        child_type, parent_type = schema.type_of(child), schema.type_of(parent)
        # Compare families, not spellings: `int` and `integer`, or a PostgreSQL
        # `serial` key with an `integer` reference, are the same column type.
        if child_type and parent_type and type_family(child_type) != type_family(parent_type):
            out.append(
                Problem(
                    WARN,
                    "fk-type-mismatch",
                    f"{child} is {child_type!r} but {parent} is {parent_type!r}",
                    target=pt,
                )
            )

        pk = schema.primary_keys.get(pt)
        if pk and pc != pk:
            out.append(
                Problem(
                    WARN,
                    "fk-to-non-primary-key",
                    f"{child} references {parent}, which is not {pt}'s primary key ({pk})",
                    target=pt,
                )
            )
        elif pk is None:
            # The table declares no primary key at all, so the reference cannot be
            # to one. Measured: this was silent, and the artifact exited 0 with only
            # `missing-primary-key` on the *other* table.
            out.append(
                Problem(
                    WARN,
                    "fk-to-non-primary-key",
                    f"{child} references {parent}, but {pt} declares no primary key",
                    target=pt,
                )
            )

    for witness, component in cycle_witnesses(schema.edges()):
        out.append(
            Problem(
                WARN,
                "cyclic-foreign-key",
                f"foreign-key cycle: {' → '.join(witness)} — inserts need deferred constraints",
                target=witness[0],
                identity=tuple(component),
            )
        )

    for table in schema.table_names():
        if table not in schema.primary_keys:
            out.append(
                Problem(
                    INFO, "missing-primary-key", f"table {table!r} has no primary key", target=table
                )
            )

    reverse_edges: dict[str, list[str]] = reverse(edges)
    for table in schema.table_names():
        if table in schema.roots:
            continue
        # A leaf that references a parent is not an orphan; a table nothing
        # points at and that points at nothing is dead weight.
        if not reverse_edges.get(table) and not edges.get(table):
            out.append(
                Problem(
                    INFO,
                    "orphan-table",
                    f"nothing references {table!r} and it references nothing",
                    target=table,
                )
            )

    if not schema.tables:
        out.append(Problem(INFO, "no-tables", "the schema declares no tables"))

    positions, r = compute_layout(schema)
    for p in out:
        if p.bbox is None and p.target in positions:
            p.bbox = node_box(positions[p.target], r)

    report.problems = out
    return report
