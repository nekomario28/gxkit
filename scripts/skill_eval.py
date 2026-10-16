"""Run the family skill with an agent that has not seen it, and grade the result.

The tools are for agents, and what makes them usable is the *skill text*. That text
is documentation, so it has no gate: a wrong sentence in `SKILL.md` breaks nothing
and no test notices. This runs the loop the way an agent meets it — a fresh
directory holding the artifact and the tool's `SKILL.md`, an independent agent
(`codex exec` by default), and a mechanical grade of the outcome:

    the inspector exits 0
    the property is re-derived from the artifact, not taken from the agent's summary
    the artifact still declares what it did (a fix, not a deletion)
    the tool's own sources are unchanged

It is **not** in `scripts/check.sh`: it needs a model, it costs tokens, and it is
not deterministic. Run it by hand after touching a skill, and record what changed —
`docs/SKILL-EVAL.md` is the last such record.

The grading half is importable (`task_problems`) and is exercised by
`packages/gxkit/tests/test_skill_eval.py`, which feeds it a correct fix, an
untouched artifact, a deletion and a patched tool. So the grader has a gate even
though the run does not.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: A level whose second one-way tile runs into a wall: three cells can be entered
#: and cannot get back to the goal, while the goal stays reachable.
BROKEN_LEVEL = '''"""The vault level."""
LEVEL = [
    "S.G##",
    ".>>X#",
]
'''

#: A declaration whose bars start at 25 instead of zero.
BROKEN_CHART = {
    "title": "Quarterly revenue",
    "x_label": "quarter",
    "y_label": "revenue (M JPY)",
    "y_min": 25,
    "marks": [
        {
            "kind": "bar",
            "categories": ["Q1", "Q2", "Q3", "Q4"],
            "values": [31.5, 34.2, 29.8, 41.0],
        }
    ],
}

PROMPT = """You are in a directory with an artifact in `{artifact}` and one document, `SKILL.md`.

Read `SKILL.md`, then make the artifact pass its own gate: the inspector must exit 0.
Fix the artifact itself; do not edit, delete or bypass `SKILL.md`, and do not install
anything. When you are done, say in one line which tool you used and what you changed.
"""


@dataclass
class Task:
    name: str
    tool: str
    filename: str
    body: str
    #: Problems with the artifact as the agent left it, `[]` when it is fixed.
    grade: Callable[[Path], list[str]]


def _grade_level(directory: Path) -> list[str]:
    from gxcore.graph import traps
    from levelgx import inspect_level, load_level

    problems: list[str] = []
    level, _module = load_level(directory / "puzzle.py")
    rows = level.rows
    report = inspect_level(level)
    if report.errors:
        problems.append(f"the level still has {report.errors} error(s): {report.problems[0].code}")
    # A fix, not a deletion: the level must still be a level.
    for tile, what in (("S", "spawn"), ("G", "goal"), ("X", "item")):
        if not any(tile in row for row in rows):
            problems.append(f"the {what} tile {tile!r} was removed instead of the fault")
    edges = {cell: level.neighbors(*cell) for cell in _cells(level)}
    if traps(edges, [level.spawn()], [level.goal()]):
        problems.append("a reachable cell still cannot get back to the goal")
    return problems


def _cells(level) -> list[tuple[int, int]]:
    return [
        (row, column)
        for row in range(level.height)
        for column in range(level.width)
        if level.passable(row, column)
    ]


def _grade_chart(directory: Path) -> list[str]:
    from chartgx.model import inspect_model, load_model

    problems: list[str] = []
    model = load_model(directory / "quarterly.json")
    report = inspect_model(model, "quarterly.json")
    if report.errors:
        problems.append(f"the declaration still has {report.errors} error(s)")
    mark = model["marks"][0]
    if mark.get("categories") != ["Q1", "Q2", "Q3", "Q4"]:
        problems.append("the categories were changed instead of the axis")
    if mark.get("values") != [31.5, 34.2, 29.8, 41.0]:
        problems.append("the values were changed instead of the axis")
    low = model.get("y_min")
    if low is not None and float(low) > 0.0:
        problems.append(f"y_min is still {low}")
    return problems


TASKS = [
    Task("levelgx", "levelgx", "puzzle.py", BROKEN_LEVEL, _grade_level),
    Task(
        "chartgx",
        "chartgx",
        "quarterly.json",
        json.dumps(BROKEN_CHART, indent=2) + "\n",
        _grade_chart,
    ),
]


def sources_digest() -> str:
    """A digest of every tool's source, so a patched tool is visible."""
    digest = hashlib.sha256()
    for path in sorted((ROOT / "packages").glob("*/src/**/*.py")):
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def task_problems(task: Task, directory: Path, before: str) -> list[str]:
    """Everything wrong with what the agent left in `directory`."""
    problems: list[str] = []
    if not (directory / task.filename).exists():
        return [f"{task.filename} was deleted"]
    try:
        problems.extend(task.grade(directory))
    except Exception as error:  # a malformed artifact is a failed task, not a crash
        problems.append(f"the artifact cannot be read back: {type(error).__name__}: {error}")
    if sources_digest() != before:
        problems.append(
            f"{task.tool}'s own sources changed; the tool was patched, not the artifact"
        )
    return problems


def _last_words(log: str) -> str:
    """The agent's closing sentence, not the harness's token count."""
    noise = ("hook:", "tokens used", "workdir:", "model:", "provider:")
    lines = [
        line.strip()
        for line in log.splitlines()
        if line.strip() and not line.strip().isdigit() and not line.strip().startswith(noise)
    ]
    return (lines[-1] if lines else "(no output)")[:200]


def setup(task: Task, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / task.filename).write_text(task.body, encoding="utf-8")
    shutil.copy(ROOT / "packages" / task.tool / "SKILL.md", directory / "SKILL.md")
    (directory / "PROMPT.txt").write_text(PROMPT.format(artifact=task.filename), encoding="utf-8")


def run_agent(task: Task, directory: Path, command: str, timeout: int) -> str:
    prompt = (directory / "PROMPT.txt").read_text(encoding="utf-8")
    argv = [*command.split(), "--cd", str(directory), "--skip-git-repo-check", prompt]
    result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    log = (result.stdout or "") + (result.stderr or "")
    (directory / "agent.log").write_text(log, encoding="utf-8")
    return log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agent-command",
        default="codex exec --sandbox workspace-write",
        help="the independent agent to run (default: codex exec, writing inside its directory)",
    )
    parser.add_argument("--timeout", type=int, default=1200, help="seconds per task")
    parser.add_argument("--keep", action="store_true", help="leave the directories behind")
    parser.add_argument(
        "--grade-only",
        metavar="DIR",
        help="skip the agent: grade a directory a previous run left behind",
    )
    parser.add_argument(
        "--task",
        action="append",
        choices=[task.name for task in TASKS],
        help="run only this task (repeatable)",
    )
    args = parser.parse_args(argv)

    failures = 0
    chosen = [task for task in TASKS if not args.task or task.name in args.task]
    before = sources_digest()
    root = Path(tempfile.mkdtemp(prefix="gxkit-skill-eval-"))
    try:
        for task in chosen:
            directory = root / task.name
            setup(task, directory)
            if args.grade_only:
                # A run with several tasks leaves one directory per task; a single
                # `--task` may point straight at one.
                given = Path(args.grade_only).resolve()
                named = given / task.name
                directory = named if named.is_dir() else given
            else:
                print(f"==> {task.name}: running {args.agent_command}", flush=True)
                log = run_agent(task, directory, args.agent_command, args.timeout)
                print(f"    agent said: {_last_words(log)}")
            problems = task_problems(task, directory, before)
            if problems:
                failures += 1
                print(f"XX  {task.name}: FAIL")
                for problem in problems:
                    print(f"      {problem}")
            else:
                print(f"OK  {task.name}: PASS")
    finally:
        if args.keep or args.grade_only:
            print(f"kept: {root}")
        else:
            shutil.rmtree(root, ignore_errors=True)
    if failures:
        print(f"\n{failures} of {len(chosen)} task(s) failed.", file=sys.stderr)
        return 1
    print(f"\nAll {len(chosen)} task(s) passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
