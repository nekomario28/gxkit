# The skill, run by an agent that had not seen it

The tools are for agents, and the thing that makes them usable is the skill text —
not the code. So the skill was evaluated the way it is used: an independent agent
(`codex exec`, a different model, no access to this repository's history, nothing
but one `SKILL.md` and the artifact) was asked to make an artifact pass its own
gate, and the outcome was graded mechanically.

## The method

Each task ran in a fresh directory holding exactly two files: the artifact and the
tool's `SKILL.md`. The prompt was the same shape both times:

> Read `SKILL.md`, then make the artifact pass its own gate: the inspector must exit
> 0. Fix the artifact itself; do not edit, delete or bypass `SKILL.md`, and do not
> install anything.

Grades, checked after the run rather than from the agent's summary:

| criterion | how it was checked |
| --- | --- |
| the gate is green | `gxkit inspect …` exits 0 |
| the defect is really gone | the artifact is re-read and the specific property re-derived (a level with no reachable trap; a declaration whose bars start at zero) |
| the fix is not a deletion | the artifact still declares what it did before — the spawn, the goal, the item; four bars with their four values |
| the tool was not patched | a hash of every `packages/*/src/**/*.py` is compared before and after |
| the right tool was used | taken from the transcript |

## Results

| task | artifact | outcome | what the agent did |
| --- | --- | --- | --- |
| `levelgx` | a level whose second one-way tile runs into a wall, so three reachable cells cannot get back to the goal | **pass** | ran `levelgx inspect`, read `soft-lock`, and turned the second `>` into `.` — the goal and the item are both still there, and exit is 0 |
| `chartgx` | `quarterly.json`, a figspec declaration with `y_min: 25` | **pass** | routed to the declared route, read `truncated-baseline`, and set `y_min` to 0, keeping all four categories and values; exit is 0 |

Both agents chose a minimal, correct fix and left the tool alone (hashes
identical). Neither needed the repository, the source, or a second document.

## What the evaluation found, and what changed

Two real gaps, both in the documentation rather than the code:

1. **A read-only directory looked like a broken tool.** The first run happened in a
   read-only sandbox; `inspect` writes `<name>.storyboard.png` beside the artifact
   by default, so it exited 2, and the agent reported "no changes possible" instead
   of fixing the level. `--no-storyboard` existed but no skill mentioned it. The
   family skill now has a **Flags that matter in a sandbox** section, and
   `levelgx`/`chartgx` mention the flag where the loop is described.
   (The behaviour itself is deliberate: the image is part of the evidence, so a
   directory that cannot hold it is an input failure, not a quiet success.)
2. **The declared route was invisible in the tool skill.** `chartgx/SKILL.md` said
   "write the chart as a Python file" and never mentioned that a `.json`
   declaration is inspected directly — so the agent, told to be careful, *wrote an
   unnecessary matplotlib renderer* to have a Python file to inspect. It still
   passed, which is exactly why the gap would have gone unnoticed: the task was
   solved by the wrong route. The loop now names the declaration first.

## Not covered

- One model of one family, two tasks, one artifact per task. This is a probe, not a
  survey: a different agent may fail differently.
- The tasks were graded on the *outcome*, not on the reading of a finding. Whether
  an agent can act on `hazard-cuts-off` or `no-exit` the way it acted on
  `soft-lock` is untested.
- The evaluation is manual: `codex exec` was run by hand, and the transcripts are
  not in this repository. Nothing in the gate re-runs it, so it cannot catch a
  regression on its own. It is evidence about the skill, not a guard on it.
