"""Read the state machine a document already draws: a Mermaid state diagram.

Diagrams are how plenty of projects actually specify a workflow, and Mermaid's
`stateDiagram` is the dialect most of them use. Converting one costs nothing and
changes no claim: the converted machine is inspected by exactly the same checks
as a declaration, so a state nothing can reach is the same defect whether it was
drawn or declared.

Only the standard library reads the document, so an importer adds no runtime
dependency.

The mapping is exact. `[*] --> s` is the start, `s --> [*]` is accepting, and
`a --> b : event` is a transition. Where Mermaid can express something the
machine cannot, the importer refuses instead of guessing: two initial states (the
machine has one start), a composite state (the machine has no hierarchy), and a
document with more than one state diagram (which one is the artifact is not a
decision worth guessing).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from gxcore.loading import InvalidArtifact

from .machine import Machine

INITIAL = "[*]"
HEADER = re.compile(r"^\s*stateDiagram(-v2)?\s*$", re.IGNORECASE)
DIRECTION = re.compile(r"^\s*direction\s+\S+\s*$", re.IGNORECASE)
ALIAS = re.compile(r'^\s*state\s+"(?P<label>[^"]*)"\s+as\s+(?P<name>[\w.\-]+)\s*$', re.IGNORECASE)
DECLARATION = re.compile(r"^\s*state\s+(?P<name>[\w.\-]+)\s*$", re.IGNORECASE)
COMPOSITE = re.compile(
    r"^\s*state\s+(?:\"(?P<label>[^\"]*)\"\s+as\s+)?(?P<name>[\w.\-]+)\s*\{", re.IGNORECASE
)
DESCRIPTION = re.compile(r"^\s*(?P<name>[\w.\-]+)\s*:\s*(?P<text>.+)$")
IGNORED = re.compile(
    r"^\s*(classDef\b|class\b|click\b|style\b|linkStyle\b|accTitle\b|accDescr\b)",
    re.IGNORECASE,
)
TRANSITION = re.compile(
    r"^\s*(?P<source>\[\*\]|[\w.\-]+)\s*-->\s*(?P<target>\[\*\]|[\w.\-]+)\s*(?::\s*(?P<event>.*))?$"
)


@dataclass
class _Diagram:
    transitions: list[tuple[str, str, str]] = field(default_factory=list)
    start: str | None = None
    accept: list[str] = field(default_factory=list)
    declared: list[str] = field(default_factory=list)


def _diagram_of(text: str, *, source: str) -> _Diagram:
    """One diagram's states and transitions, or a located rejection."""
    lines = [(number, line) for number, line in enumerate(text.splitlines(), start=1)]
    body = [(number, line) for number, line in lines if not _blank(line)]
    if not body:
        raise InvalidArtifact(f"{source}: no stateDiagram")
    if not HEADER.match(body[0][1]):
        raise InvalidArtifact(f"{source}:{body[0][0]}: expected a `stateDiagram-v2` header")
    diagram = _Diagram()
    # A `state x { ... }` block is a hierarchy the machine cannot hold; skipping
    # to its end keeps the rest readable so the refusal names the right line.
    depth = 0
    for number, line in body[1:]:
        depth += line.count("{") - line.count("}")
        if depth > 0 or line.rstrip().endswith("{"):
            raise InvalidArtifact(
                f"{source}:{number}: a composite state is not representable; "
                "declare the machine in Python"
            )
        if depth < 0:
            raise InvalidArtifact(f"{source}:{number}: unexpected closing brace")
        if DIRECTION.match(line) or IGNORED.match(line):
            continue
        if _note(line, number, source):
            continue
        alias = ALIAS.match(line)
        if alias is not None:
            diagram.declared.append(alias.group("name"))
            continue
        declaration = DECLARATION.match(line)
        if declaration is not None:
            diagram.declared.append(declaration.group("name"))
            continue
        description = DESCRIPTION.match(line)
        if description is not None:
            diagram.declared.append(description.group("name"))
            continue
        transition = TRANSITION.match(line)
        if transition is None:
            raise InvalidArtifact(f"{source}:{number}: cannot read {line.strip()!r}")
        source_state = transition.group("source")
        target_state = transition.group("target")
        event = (transition.group("event") or "").strip()
        if source_state == INITIAL:
            if diagram.start is not None and diagram.start != target_state:
                raise InvalidArtifact(
                    f"{source}:{number}: a second initial state ({diagram.start!r} is already "
                    "the start); the machine has one start"
                )
            diagram.start = target_state
            continue
        if target_state == INITIAL:
            diagram.accept.append(source_state)
            continue
        diagram.transitions.append((source_state, target_state, event))
    return diagram


def _blank(line: str) -> bool:
    stripped = line.strip()
    return not stripped or stripped.startswith("%%")


def _note(line: str, number: int, source: str) -> bool:
    """`note right of a : text` is prose about a state; a block form is not read.

    A single-line note carries its text after a colon. Without one, the note
    opens a block, which this importer does not follow.
    """
    if not re.match(r"^\s*note\b", line, re.IGNORECASE):
        return False
    if ":" not in line:
        raise InvalidArtifact(f"{source}:{number}: a note block is not read")
    return True


def machine_from_mermaid(text: str, *, source: str = "diagram.mmd") -> Machine:
    """A `Machine` from a Mermaid state diagram."""
    diagram = _diagram_of(text, source=source)
    states: list[str] = []
    for name in [*diagram.declared, *diagram.accept]:
        if name not in states:
            states.append(name)
    for source_state, target_state, _event in diagram.transitions:
        for name in (source_state, target_state):
            if name not in states:
                states.append(name)
    if diagram.start is not None and diagram.start not in states:
        states.insert(0, diagram.start)
    return Machine(
        states=states,
        transitions=list(diagram.transitions),
        start=diagram.start,
        accept=sorted(set(diagram.accept)),
        name=Path(source).stem or "machine",
    )


FENCE = re.compile(r"^\s*```+\s*mermaid\s*$", re.IGNORECASE)


def diagram_in_markdown(text: str, *, source: str) -> str:
    """The single state diagram a Markdown document draws."""
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in text.splitlines():
        if current is None and FENCE.match(line):
            current = []
            continue
        if current is not None:
            if line.strip().startswith("```"):
                blocks.append(current)
                current = None
            else:
                current.append(line)
    diagrams = [block for block in blocks if any(HEADER.match(line) for line in block)]
    if not diagrams:
        raise InvalidArtifact(f"{source}: no ```mermaid block containing a stateDiagram")
    if len(diagrams) > 1:
        raise InvalidArtifact(
            f"{source}: {len(diagrams)} state diagrams; which one is the artifact is not "
            "something to guess — extract it to its own .mmd file"
        )
    return "\n".join(diagrams[0])


def machine_from_file(path: str | Path) -> Machine:
    """A `Machine` from a Mermaid diagram, or from the block a document draws."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InvalidArtifact(f"{path}: {exc}") from exc
    if path.suffix.lower() in {".md", ".markdown"}:
        return machine_from_mermaid(diagram_in_markdown(text, source=str(path)), source=str(path))
    return machine_from_mermaid(text, source=str(path))
