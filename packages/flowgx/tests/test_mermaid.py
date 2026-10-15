"""The Mermaid importer: every branch, and the boundaries it refuses to guess."""

from __future__ import annotations

import pytest
from flowgx import (
    Machine,
    diagram_in_markdown,
    inspect_machine,
    load_machine,
    machine_from_file,
    machine_from_mermaid,
)
from gxcore.loading import InvalidArtifact

DIAGRAM = """stateDiagram-v2
    direction LR
    [*] --> cart
    cart --> address : checkout
    address --> payment : continue
    payment --> review : authorize
    review --> paid : capture
    review --> payment : retry
    paid --> [*]
    abandoned --> cart : resume
"""


def test_a_diagram_becomes_a_machine():
    machine = machine_from_mermaid(DIAGRAM, source="checkout.mmd")
    assert machine.name == "checkout"
    assert machine.start == "cart"
    assert machine.accept == ["paid"]
    assert machine.all_states() == [
        "paid",
        "cart",
        "address",
        "payment",
        "review",
        "abandoned",
    ]
    assert machine.transitions == [
        ("cart", "address", "checkout"),
        ("address", "payment", "continue"),
        ("payment", "review", "authorize"),
        ("review", "paid", "capture"),
        ("review", "payment", "retry"),
        ("abandoned", "cart", "resume"),
    ]


def test_the_real_defect_in_a_drawn_diagram_is_reported():
    report = inspect_machine(machine_from_mermaid(DIAGRAM))
    codes = {problem.code: problem.severity for problem in report.problems}
    assert codes == {"unreachable-state": "error", "cycle": "info"}


def test_the_first_header_version_is_accepted():
    machine = machine_from_mermaid("stateDiagram\n    [*] --> a\n    a --> [*]\n")
    assert machine.start == "a" and machine.accept == ["a"]


def test_an_alias_declares_the_state_under_its_identifier():
    machine = machine_from_mermaid(
        'stateDiagram-v2\n    state "In review" as review\n    [*] --> review\n    review --> [*]\n'
    )
    assert machine.all_states() == ["review"]


def test_a_bare_state_declaration_is_read():
    machine = machine_from_mermaid("stateDiagram-v2\n    state idle\n    [*] --> idle\n")
    assert "idle" in machine.all_states()


def test_a_description_line_declares_the_state():
    machine = machine_from_mermaid("stateDiagram-v2\n    busy: waiting on a lock\n")
    assert "busy" in machine.all_states()


def test_a_transition_without_an_event_still_becomes_one():
    machine = machine_from_mermaid("stateDiagram-v2\n    a --> b\n")
    assert machine.transitions == [("a", "b", "")]


def test_an_event_may_contain_a_colon():
    machine = machine_from_mermaid("stateDiagram-v2\n    a --> b : retry: again\n")
    assert machine.transitions == [("a", "b", "retry: again")]


def test_comments_and_styling_are_not_structure():
    machine = machine_from_mermaid(
        "stateDiagram-v2\n"
        "%% a comment\n"
        "    direction TB\n"
        "    classDef bad fill:#f00\n"
        "    class a bad\n"
        '    click a href "https://example.com"\n'
        "    style a fill:#fff\n"
        "    linkStyle 0 stroke:#000\n"
        "    accTitle: Checkout\n"
        "    accDescr: How money moves\n"
        "    note right of a : a single-line note\n"
        "    [*] --> a\n"
        "    a --> [*]\n"
    )
    assert machine.start == "a" and machine.accept == ["a"]
    assert machine.transitions == []


def test_a_start_state_no_transition_reaches_is_still_a_state():
    machine = machine_from_mermaid("stateDiagram-v2\n    [*] --> only\n")
    assert machine.all_states() == ["only"]


def test_repeating_the_same_initial_state_is_not_a_second_one():
    machine = machine_from_mermaid("stateDiagram-v2\n    [*] --> a\n    [*] --> a\n")
    assert machine.start == "a"


@pytest.mark.parametrize("terminal", ["paid --> [*]", "paid --> [*] : done"])
def test_a_terminal_marker_makes_the_state_accepting(terminal):
    machine = machine_from_mermaid(f"stateDiagram-v2\n    [*] --> a\n    {terminal}\n")
    assert machine.accept == ["paid"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", "no stateDiagram"),
        ("flowchart LR\n    a --> b\n", "expected a `stateDiagram-v2` header"),
        ("stateDiagram-v2\n    [*] --> a\n    [*] --> b\n", "a second initial state"),
        (
            "stateDiagram-v2\n    state outer {\n        [*] --> inner\n    }\n",
            "a composite state is not representable",
        ),
        ("stateDiagram-v2\n    }\n", "unexpected closing brace"),
        (
            "stateDiagram-v2\n    note right of a\n        multi line\n    end note\n",
            "a note block is not read",
        ),
        ("stateDiagram-v2\n    a b c\n", "cannot read"),
    ],
)
def test_a_diagram_the_machine_cannot_hold_is_refused_with_its_line(text, expected):
    with pytest.raises(InvalidArtifact) as info:
        machine_from_mermaid(text, source="diagram.mmd")
    assert expected in str(info.value)
    assert "diagram.mmd" in str(info.value)


def test_a_document_with_one_diagram_is_read_through_it():
    document = f"# Checkout\n\nProse.\n\n```mermaid\n{DIAGRAM}```\n\nAfter.\n"
    machine = machine_from_file(_write("checkout.md", document))
    assert machine.start == "cart"


def _write(name, text):
    import pathlib
    import tempfile

    path = pathlib.Path(tempfile.mkdtemp(prefix="flowgx-")) / name
    path.write_text(text, encoding="utf-8")
    return path


def test_a_diagram_file_is_read_directly():
    machine = machine_from_file(_write("checkout.mmd", DIAGRAM))
    assert machine.name == "checkout"


@pytest.mark.parametrize("suffix", [".mmd", ".mermaid"])
def test_both_diagram_suffixes_are_routed(suffix):
    machine, _module = load_machine(_write(f"checkout{suffix}", DIAGRAM))
    assert machine.start == "cart"


@pytest.mark.parametrize("suffix", [".md", ".markdown"])
def test_both_markdown_suffixes_are_routed(suffix):
    machine, _module = load_machine(_write(f"checkout{suffix}", f"```mermaid\n{DIAGRAM}```\n"))
    assert machine.start == "cart"


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        ("# No diagrams\n", "no ```mermaid block containing a stateDiagram"),
        ("```mermaid\nflowchart LR\n    a --> b\n```\n", "no ```mermaid block containing"),
        (
            f"```mermaid\n{DIAGRAM}```\n\n```mermaid\n{DIAGRAM}```\n",
            "2 state diagrams",
        ),
    ],
)
def test_a_document_that_does_not_hold_one_diagram_is_refused(document, expected):
    with pytest.raises(InvalidArtifact) as info:
        diagram_in_markdown(document, source="README.md")
    assert expected in str(info.value)


def test_a_missing_diagram_file_is_an_input_failure():
    import pathlib
    import tempfile

    with pytest.raises(InvalidArtifact, match="missing"):
        machine_from_file(pathlib.Path(tempfile.mkdtemp()) / "missing.mmd")


def test_a_python_declaration_is_still_the_other_route():
    machine = Machine(states=["a"], start="a", accept=["a"])
    assert machine.start == "a"
    from flowgx import machine_from_parts

    assert machine_from_parts(states=["a"], start="a").all_states() == ["a"]
