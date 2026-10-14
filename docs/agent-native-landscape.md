# The agent-native creative-tool landscape

Research notes (2026-10): which creative tools are designed *for* agents the way
ManimGX is — and which are not built yet.

## The pattern

ManimGX is not "a tool an agent can drive". It is a tool **designed around an
agent loop**. Five pillars, all present:

1. **A declarative code API.** The agent writes Python (`m.Scene`,
   `m.Circle(...)`), never clicks a GUI.
2. **Fast, deterministic rendering.** ~1 s of 1080p60 per second of video
   (36.2 s of video in 3.08 s on an M4 Pro; 90.6× ManimCE). Iteration is cheap.
3. **A domain-aware `inspect`.** It renders nothing, reads the scene, reports
   semantic problems (text overlap, frame overflow, unreadable text), writes a
   **storyboard image**, and **exits 1** on error. This is the pillar nobody
   else has.
4. **Agent ergonomics.** `llms.txt` / `llms-full.txt`, a statically typed API, a
   prompt-to-install flow ("paste this into Claude Code"), and errors that name
   the failing line *and the fix* (`ShowCreation is Create in ManimGX`).
5. **Ships its own skill.** The repo is usable as an agent skill out of the box.

Two ways this arrives:

- **Native** — the tool is built agent-first from scratch. ManimGX is the
  reference.
- **Wrapped** — human software is retrofitted with a CLI/MCP harness. This is
  what **CLI-Anything** (HKUDS, 52,055★, created 2026-03) does: it generates
  a CLI + SKILL.md for Blender, FreeCAD, GIMP, Kdenlive, LibreOffice, QGIS,
  Shotcut, Audacity, Rekordbox, Calibre, Obsidian, Zoom, n8n… The wrapper adds
  command surfaces and a `preview`/`live` loop; it inherits the *host
  application's* model of correctness, so it rarely has a semantic `inspect`.

## The map

| Domain | Native agent-first tool? | What exists | Gap |
| --- | --- | --- | --- |
| Math / 3D animation | **Yes** — ManimGX | the reference | — |
| Diagrams / explainers | Mostly | d2, mermaid, `vlmkit-anim` | — |
| Music / audio | Partial | `ismail` (14★, agent DAW, "can't hear so it reads"), `bounce-house` (2★, 39 mix metrics, `--json`) | no author→render→**inspect** engine; fragments only |
| Music control / analysis | Partial | `audio-analyzer-rs` (MCP, 66★), loudness CLIs | — |
| Data visualization | **No** | `FigureLint` v0.1.0 (academic figures) | **no general chart inspector** |
| Video timeline editing | Only wrapped | Kdenlive/Shotcut via CLI-Anything | native editing + timeline inspect |
| CAD / 3D printing | Only wrapped | FreeCAD, build123d | native with design-rule inspect |
| Image editing / photography | Only wrapped | GIMP via CLI-Anything | native with composition checks |
| Presentations / slides | Skill only | `huashu-design` (24,902★, an HTML design skill) | native layout inspector |
| Document / typography | Proto | LaTeX `overfull` warnings are a proto-`inspect` | first-class layout inspect |
| Shader / GPU graphics | **No** | — | the whole quadrant |
| Game / level design | **No** | — | a playtest/feedback loop |

## The empty quadrants (strongest first)

1. **Data visualization.** Agents emit matplotlib constantly and nothing checks
   whether the chart is *honest*. The classic failure — a bar chart whose
   baseline is truncated, turning 8% into 300% — is mechanical to detect and
   nothing detects it. Only `FigureLint` exists, and it lints academic figures,
   not correctness. → **built in `gxkit` as `chartgx`.**

> **Status (v0.8.0):** `gxkit` implements this pattern for fifteen domains —
> charts, game levels, state machines, permissions, module graphs, schemas,
> pages, protocols and fragment shaders — over one core (`gxcore`). See the
> repository README for the current list.
2. **Shader / GPU graphics.** No agent-first shader authoring loop with a
   pixel-verified `inspect`.
3. **Game / level design.** No engine that lets an agent build a level and then
   *play it back* as structured feedback (collisions, reachability, soft-locks).
4. **Video timeline editing.** Native timeline assembly + a "continuity/audio
   inspect" does not exist as a tool; it is wrapped applications.

## Design principles worth copying

Gathered from ManimGX and `ismail` (whose `AGENTS.md` is unusually good):

- **Give the agent eyes that return text.** `ismail`: "the agent can't hear what
  it made… every render becomes text the agent reads." `chartgx` does the same
  for charts: problems are codes + messages, plus an image for vision models.
- **Exit codes are the API.** A linter an agent cannot gate on is a suggestion.
- **Separate error / warn / info.** Wrong vs. broken vs. a reviewer's note.
- **Prove each check can fail.** A check with no failing test is decoration.
- **Bundle the toolchain.** ManimGX ships fonts, typesetting and H.264 so
  "install" is one line. Any external dependency is a place the loop dies.
- **Ship the skill and the llms.txt.** The tool's instructions are part of the
  tool.
- **"Their words, not ours"** (`ismail`). Never make the person learn the tool's
  vocabulary; the agent installs and runs it.

## Adjacent tools, and what gxkit is not

gxkit is a *semantic* inspector, so it overlaps a different neighbour in each
domain and beats each on one axis: it decides **what is wrong**, with a stable
code, not merely **what changed**.

| Neighbour | What it does | Where gxkit differs |
| --- | --- | --- |
| Visual-regression / snapshot tools (Playwright, Percy, Chromatic, pytest-mpl, reg-viz) | diff an image against a golden baseline | no baseline: it judges the artifact against a **rule** ("a bar baseline must start at 0"), and works on a first render |
| LLM / VLM reviewers | look at the picture and describe it | deterministic, offline, stable codes, gateable; no hallucination budget |
| Code linters / type checkers (ruff, mypy, eslint) | inspect source | inspect the **artifact the source produces** — pixels, graphs, reachability |
| Domain linters (buf, sqruff, glslangValidator, d2/mermaid) | validate syntax/shape in one format | one contract across fifteen domains; catches *semantic* faults (a black frame, a soft-lock, an unused uniform), not only compile errors |
| ffprobe / media-info | report metadata | decide "frozen / black / silent / wrong length / no motion" |
| MCP browser / devtools harnesses, CLI-Anything | drive a tool for the agent | judge the result; the loop, not the driver |

Wrong tool when: you want a pixel diff against a baseline (use a VRT tool), a
formal proof (use TLA+/Alloy), or you are inspecting a domain with no rule set
— there, add a tool (`docs/BUILDING.md`). gxkit does not render: the host
renderer (matplotlib, ffmpeg, GL, the grid) produces the artifact; gxkit reads
it.

## Method / provenance

Repos and counts read from the GitHub API and PyPI on 2026-10-13; ManimGX
claims from <https://manimgx.academa.ai/> and its `llms.txt`. Star counts for
young projects (2026) are small and not a quality signal — `ismail` at 14★ is
still the clearest native agent-DAW design.
