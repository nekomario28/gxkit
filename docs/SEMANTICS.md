# What each check's claim was measured against

A code is a claim. `soft-lock` claims a cell you can enter and not leave with the
goal still reachable; `overlap` claims two runs hold one resource at once;
`dangling-reference` claims a declared name resolves to nothing. A check that
fires on the wrong thing, or stays quiet when the claim is violated, is worse than
no check — so each claim needs evidence, not an argument.

This file records that evidence. It is the counterpart of `docs/IDENTITY.md`:
that one is generated and counts what a finding is identified by; this one is
written and says what each finding was *tested* to mean.

## How the claims are held

Three layers, and they answer different questions:

| layer | question | mechanism |
| --- | --- | --- |
| the example tests | does the check fire when the defect is present? | `examples/broken_*.py` and `examples/good_*.py`; `scripts/check_mutations.py` removes each check and requires the test to fail (112 mutants) |
| the property tests | is the *algorithm* the one it claims? | cross-checked against NetworkX / Shapely on seeded random artifacts |
| the probes below | does it fire only when the claim is violated, and for every instance? | hand-built adversarial artifacts, run in a session and recorded here |

The middle layer is why the traversal-based tools (`levelgx`, `netgx`,
`depsgx`, `flowgx`, `protogx`, `pipegx`, `authzgx`, `schemagx`) can be trusted on
paths longer than the examples: their reachability is compared with an independent
implementation rather than with itself.

## Probed in this pass

| tool | claim | probe | result |
| --- | --- | --- | --- |
| `levelgx` | `soft-lock` = reachable, goal unreachable from here | one-way dead end beside a safe route; two one-ways in a row; a *directed loop*; a trap beside the goal; a goal behind a one-way; a walled-off goal | correct. A cell you cannot reach is `unreachable-area`, not a soft-lock; a level whose goal was never reachable is `goal-unreachable`, not a soft-lock. The tile semantics cannot form a directed cycle at all (each one-way accepts entry only along its own arrow), so every soft-lock is a dead end reachable from the spawn |
| `levelgx` | diagonal is not a move | `S#`/`#G` | correct — `goal-unreachable` |
| `levelgx` | `hazard-cuts-off` = the hazard is what blocks | a hazard across the only route, and the same hazard with a way around | correct |
| `crongx` | `overlap` = half-open intervals on one resource | adjacent runs, contained run, different resources, unspecified resource, zero/negative/infinite duration | correct, and each overlapping **pair** is its own finding identified by `(resource, a, b)` |
| `netgx` | `public-reaches-sensitive` is transitive | `public → mid → sensitive`; through a cycle | correct |
| `docgx` | `clipped-text` is measured, not estimated | a long unbroken word; CJK; a block past the right edge; a 1×1 page; many lines | correct — the boxes come from PIL's font metrics, and the renderer draws from those same boxes |
| `pipegx` | `needs` are step names, `produces` are artifacts, order does not matter | a goal produced by a *later* step; a step needing a step declared later; a goal no step produces; a duplicated artifact; a cycle | correct |
| `seedgx` | `missing-seed` is about *absence*, not falsiness | `seed=0`; `seed=None`; a negative seed; `2**64`; two streams sharing a seed; `deterministic=False` | correct — `0` is a seed, `None` is missing, and the range/duplicate/non-determinism claims fire on their own cases |
| `framegx` | `frozen` means the picture does not change; `all-black` means nothing was drawn | a real moving clip; a still clip encoded as video; an all-black clip; a clip changed for one frame | **corrected**: at the default 2 samples/s a single changed frame *does* read as `frozen` (a >1.5 s run of identical samples), which the second audit called an overstated message and this line had called clean. The message now says what was compared ("identical at every sampled moment …"), and `all-black` is decided by the brightest pixel — a white 16x16 mark on a black frame was reported as "nothing was drawn" because the check averaged |
| `authzgx` | `escalation` is transitive through inheritance | one hop, three hops, two sensitive permissions | correct, with the path in the message |
| `flowgx`, `protogx` | `unknown-state` for a state nobody declared | a transition to/from an undeclared state | correct |

## Defects this pass found — all fixed

| tool | what was silent | now |
| --- | --- | --- |
| `authzgx` | a `low` principal or `sensitive` permission that is not declared was skipped, so a typo made "no escalation" an answer about a different question | `dangling-reference` names the field and the name |
| `netgx` | a `sensitive` name that is not a node was skipped — and when *none* of them is a node, `sensitive_nodes()` falls back to every `data` node, so the exposure answer silently became about a different set | `dangling-reference` |
| `depsgx` | a `forbidden` pair, a layer member or a `roots` entry that names no module was ignored, so the rule stopped being a rule | `dangling-reference` |
| `schemagx` | a `roots` entry that names no table was ignored | `dangling-reference` |
| `protogx` | a `terminal` state that does not exist produced a confusing `deadlock`; a `requests` key that names no message was ignored | `unknown-state` names it; `unknown-message` covers the request |
| `flowgx` | an `accept` state that does not exist produced a confusing `dead-end` | `unknown-state` names it |

## Known, and deliberately left

- **Two blocks with identical text overlapping are not reported** (`docgx`). The
  renderer draws them on top of each other, so the picture is the same as one
  block's — the declaration is redundant, not misleading. Reported instead is
  `text-overlap` for texts that differ, where the reader loses one of them.
- **`apigx.auth_schemes` is descriptive.** Endpoints carry `auth: bool`, not a
  scheme name, so there is no declared set for a scheme to resolve against; an
  unknown name there is documentation, not a broken reference.
- **`shadergx`'s `black-output` has a threshold, and the finding is about
  visibility.** Probed through the real GL path: mean output 0.0 and 0.005 are
  `black-output`, 0.02 and above are `constant-output` instead, and a genuinely
  dark *gradient* (0 → 0.05) is clean — so the claim holds in the direction that
  matters (nothing that varies is called black). The README said "fully
  transparent/black" while the check is `mean < 0.02`; it now says what the check
  does. NaN in any channel, including alpha alone, is `nan-output`, and an infinity
  is too — the message already said "NaN or Inf".
- **`levelgx`'s one-way tiles cannot express a directed cycle.** Each one-way
  accepts entry only along its own arrow, so a ring of them is a set of dead ends.
  That is a fact about the legend, recorded because it bounds what `soft-lock` can
  ever be: a dead end reachable from the spawn, never a loop the player is stuck
  in.

## Reviewed by an independent agent, pointed at the contract

`codex` (the usual independent reviewer) had hit its quota, so the review ran through
`opencode` with `deepseek-v4.1-flash-free`: one prompt, read-only, told to falsify
`docs/CONTRACT.md`'s Stable section and to report only what would make a promise false
or break a consumer who relies on it. It found **six**, none of which any test had
been aiming at. Every one was reproduced here before it was fixed, and each fix
carries a test and a mutation.

| # | what it found | reproduced as | now |
| --- | --- | --- | --- |
| 1 | A baseline record's `identity`, `target` and `label` were never validated. `identity` written as a *string* iterates into characters, never matches, and reports the same finding as **both new and fixed** — a broken gate. Written as an *int* it raised a bare `TypeError`, naming neither the field nor the index the contract promises. | `new: 1, fixed: 1, new_errors: 1` with nothing changed | every optional field is validated with `problems[i].<field>` named (`test_a_record_shape_that_would_match_wrongly_is_refused_with_field_and_index`) |
| 2 | `.gxkit.toml` accepted `[chartgxx]` — a table for a tool that does not exist — so a typo'd rule was inert and silent. | exit 0, no message | the umbrella validates table names against the registry (`[chartgxx] is not a tool; known tools are […]`); a single tool cannot judge and does not pretend to |
| 3 | `apigx` read the document root, `info` and `components` with `.get()` and never checked them, so an unknown root key or a misspelled `titl` reported **clean**. | `errors 0, problems []` | every key at every level is accounted for, `x-` extensions allowed; a `paths` key that is not a path is refused too |
| 4 | `schemagx` matched `UNIQUE`, `CHECK` and `EXCLUDE` in `CREATE TABLE` and then dropped them; `NOT NULL` and `DEFAULT` went the same way. | `inspect: 1 problem (0 errors)` — an unrelated notice | a **`not-modelled`** info per table naming the clauses, while reference integrity is still checked. The contract's "silence is never a verdict" now reads *refused **or reported as not carried***, which is what the tools do |
| 5 | `chartgx` publishes `.json` in the registry and `docs/TRACE.md` while the contract named **three** document readers — and `inspect -o sb.png` on a declaration wrote **no file** and exited with the inspection code, so a CI step publishing the image would publish nothing and pass. | `keys: [... no storyboard …]`, no `sb.png` | the contract names the fourth reader (and says it has no storyboard here); an explicit `-o` that cannot be honoured is **exit 2** naming the reason |
| 6 | `docs/TRACE.md`'s "codes" column is a *count*, while the contract sent a reader there for the code set. | the column reads `25` | the column says `codes (#)`, and the contract sends the reader to `gxkit codes` for the set |

It also listed what it checked and found nothing in: no documented exit code that
cannot occur, no JSON key missing sometimes (82 runs across 16 tools), no flag that
does nothing, no documented input refused, and no case where `inspect` and the
storyboard disagree about which problem is which. That list is the useful half of a
review: it says where *not* to look next.

## Second review: the *semantics* of the checks, attacked

The same instrument (`opencode` with `deepseek-v4.1-flash-free`), a different prompt:
falsify each check's **name** on adversarial artifacts, in both directions — fires when
the claim is false, silent when it is true. It attacked every code in sixteen tools and
found **twelve**; every one was reproduced here, and eleven changed behaviour or wording.
Ten now have a test and a mutation (138 in the catalogue).

| # | code | direction | what the artifact showed | now |
| --- | --- | --- | --- | --- |
| 1 | `netgx` `public-reaches-sensitive` | false positive | `sensitive=["ghost"]` produced an exposure of a node the artifact never called sensitive (on top of `dangling-reference`), and an empty list reported `db` as "sensitive" without saying the reading was by kind | a declared list is authoritative (no fallback); the by-kind reading says so in the message |
| 2 | `framegx` `all-black` | false positive | a white 16×16 mark on a 160×90 black frame (1.8% of the area) was "nothing was drawn" — the check averaged the frame | the brightest pixel decides |
| 3 | `schemagx` `fk-to-non-primary-key` | false negative | a reference to a table that declares **no** primary key produced only `missing-primary-key` on that table, exit 0 | the reference is reported |
| 4 | `pipegx` `cycle` | false negative | `Step("build", needs=["build"])` — a one-node cycle — reported a clean pipeline that can never run | reported |
| 5 | `chartgx` `clipped-data` | false negative | with **categorical x** (the common idiom) out-of-range y data was never reported; converting the labels raised and the line was skipped | the y comparison runs whatever x is |
| 6 | `flowgx` `ambiguous-transition`, `protogx` `nondeterministic` | false positive | the same transition listed twice was "non-deterministic"; the genuinely ambiguous case (two targets) looked identical to it | only different targets are ambiguity |
| 7 | `flowgx`/`protogx` `no-exit` | false negative (by name) | a dead end that also cannot finish gets `dead-end`/`deadlock` only, while the documents defined `no-exit` without that exception | the two codes are exact in the documents: `no-exit` is a state that *has* a way out and still cannot finish |
| 8 | `depsgx` `orphan-module` | false negative | a module whose only in-edge was its own self-loop counted as depended upon | a self-edge is not a user |
| 9 | `framegx` `frozen` | overstated | a one-frame change reads as frozen at 2 samples/s, and the message said "the picture is unchanged" | the message says what was compared; this file's earlier claim is corrected above |
| 10 | `docgx` `too-much-text` | false negative | a 100-word *title* against a 10-word budget passed: the title was not counted | the budget counts the page |
| 11 | `apigx` `unversioned-path` | overstated name | `/v2/items` under base `/v1` is versioned; the code said otherwise (the message was accurate) | renamed `path-outside-base`, with the rename recorded in the CHANGELOG |
| 12 | `seedgx` `invalid-seed` | unreachable | a boolean, float or string seed was refused at *load*, so the catalogued check could never appear in a report | the value is carried and the check reports it; only a non-scalar is an input failure |

The sound list matters as much: `levelgx` (`soft-lock` on one-way traps, a trap beside
the goal, an item inside a trap, `hazard-cuts-off` in three configurations),
`crongx` (half-open intervals, contained runs, non-finite times), `schemagx` (dangling
keys, 2- and 3-table cycles, type families), `depsgx` (layers, forbidden edges),
`authzgx` (transitive escalation, cyclic inheritance), `docgx` (measured text, real
overlaps), and the rest were attacked on boundary artifacts and behaved as their names
claim. Two of the twelve were found *because* the first audit's record was wrong — a
review of the record, not only of the code.

## Third review: the *importers*, against the formats they read

Same instrument, third prompt: the four readers that translate a document a project
already has — OpenAPI 3 (`apigx`), SQL DDL (`schemagx`), Mermaid `stateDiagram`
(`flowgx`) and a chart declared as data (`chartgx`) — attacked with documents built
from the formats. **Fifteen findings**, every one reproduced here; the first group is
the dangerous one, because a wrong translation is a verdict about a document the tool
did not actually read.

**A valid document read wrongly (a verdict on a misreading):**

| what the document said | what the tool said |
| --- | --- |
| `paths: {"x-internal": {…}}` — a specification extension holding data | a second endpoint, `GET /v1/x-internal` |
| `responses: {"201": {}, "5XX": {}}` — it documents an error range | `no-error-status`: "documents no error status" |
| `DEFAULT 'see REFERENCES users for detail'` — text in a column | a foreign key, and a type mismatch against it |
| `KEY idx_email (email)` — an index | a column named `KEY` |
| `CONSTRAINT "users pk" PRIMARY KEY (id)` — a key the quoted name introduces | `missing-primary-key` |
| `note --> done : finish` — a transition from a state named `note` | the transition deleted, then `dead-end` and `unreachable-state` |
| `[*] --> [*]` — the start marker is accepting | a state literally named `[*]` |

**A valid document refused:** a scalar `x-` extension; `) WITHOUT ROWID` and
`) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4` (every MySQL dump); `DEFAULT 'see references
section below'`, refused with a diagnosis naming a table that does not exist.

**An invalid document accepted, and judged as if it stated facts:**
`security: {"apiKey": []}` (an object where an array is required) read as *anonymous*,
so a mutation was reported public; `"deprecated": "false"` read as deprecated, because
`bool("false")` is true; an operation with no `responses` — which OpenAPI marks
**REQUIRED** — read as a valid API with an undefined status set; and, in the declared
chart route, `y_scale: "logarithmic"` silently falling back to linear (disabling every
log check), an unknown key inside a series, `width: "wide"`, and a heatmap with `y_min`
— all four of which the renderer that owns the model refuses.

**What changed.** The importers now: skip `x-` keys where they iterate paths; keep
`5XX`/`default` as statuses (a range is not a number, and the check understands one);
refuse a malformed `security` and a non-boolean `deprecated`; require `responses`; mask
string literals before matching DDL clauses, so a keyword in text is text; recognise
index clauses and table options as clauses the model does not carry (reported, not
refused); accept a quoted constraint name; and, in the declared route, check the closed
sets, the field types, the series fields, and the heatmap axis setting (a new code,
`inapplicable-axis-setting`, matching the renderer's). Eleven mutations were added —
**149** in the catalogue.

**The sound list**, so the next reviewer can differ deliberately: OpenAPI security
inheritance, `security: []`, `security: [{}]`, path templating, path-item/operation
`servers`, `$ref` refusal and unknown-key refusal in `info`; quoted identifiers,
column- and table-level keys, composite-key refusal in DDL; `direction`, `%%`
comments, `classDef`, a single-line note, plain transitions and the start/accept
markers in Mermaid; unknown top-level keys, mark kinds and colour ramps in the declared
chart.

## Fourth review: the sibling route, against its own project

figspec — the renderer that owns this model — was reviewed the same way (its
`docs/SEMANTICS.md` has the record; eighteen findings, all fixed there). Three
of its findings are about *this* project's declared route, and one is fixed here:

- **`y_err` carrying `NaN`.** `chartgx` reported a clean figure (exit 0) for
  `"y_err": [NaN, 0.1]` while figspec refused to parse the file at all. A magnitude
  is drawn, so it is `non-finite-value` (error) now — the negative test missed it
  (every comparison with `NaN` is false) and so did the coordinate test (it is not
  a coordinate).
- **Not fixed, deliberately.** The two routes keep their own codebooks
  (`no-axis-label`/info here against `no-xlabel`/warn there) and this one emits
  additional codes (`empty-chart`, and `mismatched-lengths` for an empty array)
  without changing the error verdict. Each codebook is stable for its own
  consumers, and folding one into the other would break them.
- `width: 0` and column-axis label ambiguity are refused by figspec's reader; this
  route refused the first already (exit 2) and gained the second in review three.

## Fifth review: the command-line and configuration surface

The same instrument, a fifth prompt: the *surface* rather than the semantics — routing,
the exit-code table, `.gxkit.toml`, the baseline, and `-o`. Thirteen findings; every one
reproduced before it was fixed, and the guards carry mutations (157 in the catalogue).

**The exit-code table was the weakest part, because it promised more than the process
could enforce.**

- `os._exit(0)` printed nothing and exited 0 — read as "inspected, no error" — and
  `os._exit(42)` exited 42, a code not in the table. `sys.exit` was caught; the
  *other* way to end a process was not. The loader traps it while the artifact runs,
  and refuses with `the artifact called os._exit(0)`.
- A FIFO named `*.py` blocked forever (`Path.exists()` is true for one, and
  `read_bytes` waits), so a directory run holding one produced no report and no exit
  code at all. Only a regular file is read.
- `KeyboardInterrupt` escaped as a traceback from the entry point with exit 130.
  Ctrl-C and an artifact raising it are the same event, so 130 is now a documented row
  (with a line, not a traceback) — and both entry points answer it the same way.

**A configuration that names nothing looked active.** A misspelled code in `ignore`
(`soft-lok`) ignored nothing; a misspelled `[severity]` name (`no-ylabels = "error"`)
left every gate green — in the file the user wrote to make the gate stricter. The
umbrella now validates code names against the codebook (it knows every code); a single
tool still cannot judge a sibling's table, which is documented rather than papered over.

**The baseline's guard did not cover provenance.** The shape guard exists, in its own
words, because "a record that never matches would report every finding as fixed or
new" — and a *chartgx* baseline compared against a *levelgx* artifact reported exactly
that ("1 new, 2 fixed", the level's error apparently paid). The baseline file has no
tool field, so the test is the codebook: a baseline whose codes are all unknown to the
tool being run is refused. The **name** is deliberately not the test — writing a
baseline from one revision and comparing another is the normal workflow. Also
`--write-baseline` combined with a missing `--baseline` ran the comparison first and
left the requested baseline unwritten; the write comes first now.

**Routing hid a second artifact.** A file declaring both a `Level` and a matplotlib
figure was routed to chartgx by registry order and reported "no problems", while
`levelgx <file>` found `no-goal` — the umbrella exit 0. Detection collects *every*
match and the ambiguity is refused with the tool to name. The contract also said
detection was automatic without saying what it reads: a builder-only artifact
(`build()`) and a file with no `.py` suffix need the tool named, which the contract now
says.

**An OpenAPI document with a reference was read as complete.** Only the path-item and
operation cases were refused, so `$ref` in `parameters`, `requestBody` or a response
schema was accepted (exit 0); no reference is resolved anywhere, so the document was
not fully read. A document-wide walk refuses the first one with its location, and the
two per-place checks it makes unreachable were **deleted** rather than kept for
appearance. A response entry that is not an object, and a `responses` that is not an
object (`null` was read as "documents no status"), are refused with their field.

### Attacked and found sound

Directory runs (`max(rc)`, empty → exit 2, good+bad mix → exit 1, a directory named
`d.py` treated as a directory); `--json` against the human report on every tool example
(same exit code, same error count, same sorted list, `storyboard`/`baseline` keys
exactly when printed); document routing by suffix, including the umbrella refusing to
auto-route a non-Python file and naming every reader; config precedence (nearest
ancestor wins, a cwd-only config is ignored for an artifact elsewhere, `--no-config`
bypasses even a malformed file) and every refusal shape (unknown top-level key,
`ignore` as a string, an invalid severity, a mistyped key in a tool table); baseline
write failures (a directory, a read-only dir) and shape refusals (version, record field
types, `identity` as an int); `-o` on every path — written, bad suffix, a directory, an
unwritable path, a declaration with no storyboard (refused), a directory run with `-o`
(refused) — with **no path where `-o` was silently skipped**.

Also: a symlink loop, a file deleted between listing and reading, unicode names and
messages on an ASCII console, and extreme numeric values (`NaN`, `∞`, `10¹⁰⁰`, 2³²
bounds) across seven tools were handled, not crashed.

## Sixth review: the shared core

The same instrument, a sixth prompt: what all 16 tools inherit — `geometry`,
`layout`, `storyboard`, `diagram`, `report`, `model`, `baseline`, `graph`. Six
findings, every one reproduced before it was fixed; the catalogue is at 163.

**One shared helper had a rule the domains disagreed about.** `cycle_witnesses`
skipped size-one components, so `authzgx` reported `editor -> editor` (a role that
inherits itself — an escalation loop) as **clean**, while the same cycle spread over
two roles was an error. The other side is real too, and this is why the fix is a
parameter rather than a flag flip: a table whose foreign key points at itself is how a
self-referencing tree is written (`schemagx`'s own property test says "a self-reference
is a tree, not a cycle"), a module that imports itself has its own `self-dependency`
finding (`depsgx`), and a state or protocol step that returns to itself is a retry
whose real fault — no way out — is `dead-end`/`no-exit` (`flowgx`, `protogx`).
`cycle_witnesses(edges, *, self_loops=True)` now states the graph rule, and each caller
chooses for its domain in one visible place.

**`intersecting_pairs` inverted its own docstring.** It reported the fraction of the
*larger* box (`both_covered`, i.e. `min`) while documenting "of the smaller", so a
small box entirely inside a big one scored 0.01 and was reported as no collision at
all — the same defect `layout.check` had fixed with its own inline copy of the rule.
It now computes the fraction of the smaller and compares `>=` ("at least"), and
`layout.check` uses the same expression, so the rule has one spelling. The Shapely
property test's *reference* was `min(...)` too — it had been written to mirror the
code, and a reference that mirrors the code proves only self-consistency.

**`layout.check` skipped pairs that shared their text, wherever they were.** Two boxes
both called `"same"`, one 0.72 inside the other, were accepted. The skip is now "the
same text in the same place", which is what it was for.

**A newline in a label lost the whole storyboard.** Pillow cannot measure a
multi-line string, and a tool's name is arbitrary: a dependency graph with a module
named `"a\nb"` raised `ValueError` and only a stderr line remained (exit 0 without
`-o`, 2 with). `gxcore.toolkit.one_line` flattens control characters for the
storyboard, and the diagram draws the flattened label.

**`identity: null` was accepted by the loader and crashed `compare`.** The guard
rejects only a *non-None* identity of the wrong type, so `null` — the legal encoding
of "no identity", as for every other optional field — reached `tuple(None)`. The
key treats it as empty.

**An unplaceable box lost the storyboard** (a finding with a `NaN` bbox): rounding it
raised, and the view of the report died with it. The number keeps the sorted position
the printed list shows; no rectangle is drawn for it. The finding itself is still in
the report, which is where the verdict lives.

### Attacked and found sound

`geometry`'s `area`/`overlap`/`covered`/`both_covered`/`union`/`clipped`/`canvas_box`
against Shapely on hand-computed values (edge-touching boxes → 0, zero-width and
negative boxes → area 0, `union([]) is None`, `clipped` at exactly the tolerance vs
just past it, all four edges named); `layout`'s `small-text` boundary and its
`clipped-text` delegation; `storyboard` numbering against `Report.sorted()` including a
bbox-less finding keeping its number, two findings on one object grouped into one
rectangle, non-RGB image modes (`L`, `RGBA`, `P`), empty/1×1/2000×2000 images, and an
edge box; `report`/`model` human text against JSON (same count, same order, no collapse
and no double print), stable `sorted()` for equal keys, `as_dict` omitting empty
optionals; the exit policy with warn/info only and with a severity override; `baseline`
wrong-typed fields, code prefixes (`"a"` vs `"ab"`), `b"/c"` vs `"b","c/"`, `identity=()`
as no identity, occurrences matched one-for-one, an empty baseline, and `new_errors`
counting only errors among new; `graph` self-loop/duplicate-edge/two-node-cycle/unknown
node through `find_cycle`, `reachable`, `weak_components`, `topological_sort`, `traps`
against NetworkX, and a 10 000-node chain and cycle staying linear; `diagram` labels
with `<`, `&`, `"`, an emoji and a 300-character word (it is raster: PIL does no string
escaping, so double escaping is structurally impossible), no nodes, deterministic
layout, and unknown edge endpoints; `backslashreplace` on an ASCII console.

### Recorded limits (not defects)

`layout.check`'s overlap loop is O(n²) — 4000 boxes take 4.75 s; no scalability is
claimed. NaN coordinates in `geometry` score 0.0 for `area`/`overlap` (Python's
`max(0.0, nan)` is `0.0`); a box with inverted coordinates has `area == 0` and is not
`clipped`. The `clipped-text` tolerance is 2 px, which is why a 1 px overflow is not
reported.

## Seventh review: the declaration route

The same instrument, a seventh prompt: the *declarations* an agent writes — every
tool's module constants, dict shapes and Python-constructed models — for the twelve
tools the document review did not cover. Seven findings, each reproduced first; the
catalogue is at 171.

**A recognised declaration was silently re-shaped, and the tool then reported a
verdict about something the file did not declare.** This is the whole class:

- `STATES = "ab"` became the states `a` and `b`; `MODULES = "abc"` a three-module
  graph with a build order; `GRANTS = ["rp"]` an invented role→permission grant; and
  `TRANSITIONS = [("a", "b", "e", "extra")]` dropped `extra` without a word. Each tool
  now converts its constants with `convert_names`/`convert_pairs` and refuses a string
  (or a wrong-arity tuple) by field and index.
- `BLOCKS = "hi"` became one block per character — and the report then said the blocks
  `h` and `i` overlapped. A block with a mistyped key (`{"colour": ...}`) raised a
  `TypeError` naming no field or index.
- `network = {"nodes": "ab"}` raised a bare `ValueError` inside `netgx`'s converter,
  which `resolve` **swallows** (it re-raises only `InvalidArtifact`) — so a second,
  clean `NETWORK` in the same module was inspected instead, and with only the
  malformed declaration the tool said "no network found". The converter validates its
  own members now.
- `secret = "no"`, `DETERMINISTIC = "no"` and `EXPECT_AUDIO = "no"` were all `True`
  (`bool("no")`), so the tools asserted the *opposite* of the declaration: a
  `secret-with-default` error, a `deterministic` verdict, an expected audio track.
  `convert_bool` refuses a non-bool. The OpenAPI importer had guarded this for
  `deprecated` since its own review; the declaration route had not.
- `{"endpoints": [{}]}` inspected as a clean API with one `GET /` endpoint the file
  never named; an endpoint declaration now states its method.

**Two routes to one concept disagreed.** `chartgx`'s figure route checked
`ax.lines` only, so a bar of 0 on a log axis — `log-nonpositive` as a declared model —
was clean as a figure; bars are `ax.patches` and are checked now. And `schemagx`'s SQL
route cannot express `roots`, so the same schema gained `orphan-table: nothing
references 'users'` where the Python route was clean: `Schema.roots_modelled` records
that the reader could not express them, the rule that needs them does not apply, and
the gap is said out loud as `not-modelled`.

### Recorded limits (measured, not defects)

**Inspection is super-linear in a few tools, and a very large declaration never
finishes**: `crongx` compares every pair of runs (5 000 runs 8.3 s, 10 000 runs 33.8 s,
100 000 runs no report after 60 s), `protogx` 40 000 transitions 35 s, `flowgx` 8 000
transitions 20 s, `authzgx` 5 000 findings 25 s. `depsgx` (20 000 modules) and `seedgx`
(20 000 streams) answer in under 0.2 s, so this is per-tool arithmetic rather than a
shared one. These are human-scale diagnostics; the numbers are here so the next
review can decide whether to flatten them.

**Field validation stops at the loader.** A *wrong-typed field* inside an
already-constructed model (`Run("a", start="oops")`, `Shader(size=("a","b"))`,
`Video(expected_duration="2.0")`) is not checked where the model is built, so the
inspector raises and the CLI reports exit 2 with the Python exception rather than a
located refusal. The converters refuse a wrong-typed member; the dataclasses do not
validate their fields.

**`apigx`'s two routes treat the base differently, deliberately**: the Python model
keeps `base` separate and checks each path against it (`path-outside-base`), while the
OpenAPI reader builds the path *in* the server's coordinate space, so a path outside
the base cannot arise. Both readings are documented; they are not the same statement.

### Attacked and found sound

Every tool's empty declaration (`[]`, `{}`, `""`, and a valid object with every
collection empty) produces a code — all fifteen — and never a silent clean;
`convert_items`/`convert_names` refusals carry field and index exactly (`runs[0]`,
`STEPS[0]`, `REFERENCES`, `endpoints[0]`); subclass members load through `isinstance`;
extreme values (`10**30`, `1e308`, `-0.0`, `NaN`, `inf`), a 10 000-character name,
`\x00`, combining, RTL and emoji names do not crash and are reported where they mean
something (`non-finite-time`, `zero-duration`); the process-exit trapping holds on this
route too; `chartgx`'s declared JSON refuses unknown keys, wrong scales, a mapping
`marks`, a string `y_min` and an unknown ramp with a location, and turns `NaN`
coordinates into `non-finite-value`; `depsgx`/`seedgx` stay linear at 20 000 members.

## Eighth review: the drawn output

The same instrument, an eighth prompt — and the first to open the pixels: every verdict
this family gives comes with a storyboard, so a picture that shows something other than
what the report says is a wrong deliverable. Five findings, each measured by probing the
PNG rather than by reading the renderer; the catalogue is at 176.

**The numbers in the picture did not always match the numbers in the text.** A
`clipped-text` finding puts its box at or past the edge, and the storyboard clamped only
the tag's left edge: measured, three such findings drew **one** number and two nothing
(one box entirely right of the canvas, one entirely below it), while the text report
listed all three — against the claim that "problem [3] in the text is box 3 in the
image". `visible_box` intersects the rectangle with the canvas and `tag_origin` places
the tag inside it whatever the box did, so every number is drawn and a box at the edge
becomes an edge strip — which is what the finding says.

**And a shared box could not draw all of its numbers.** Twelve findings on one rectangle
produced the tag `1,2,3,4,5,6,7,8,9,10,11,12`, which ran off the right edge with numbers
7-12 undrawn (`n = 10, 12, 14, 20, 30` all render identically clipped). Consecutive
numbers are compressed into ranges — `1-12` — so the tag names every finding and fits.

**A self-loop on the top node was clipped by the canvas.** The arc is drawn above-right
of its node, and for the top node that put it at `y = -10.8`: the *shipped*
`schemagx` example painted edge pixels on **row 0**, while the property test asserted
"nothing spills off the canvas" — checking the node boxes, never the arc. The loop is
translated back inside (only the near edge is reachable: the layout keeps node circles on
the canvas, so a loop is never off the far edge — the far branch was written, then
deleted, because no input reaches it and a branch nothing can reach is a line nothing can
check).

**The picture could decide the verdict.** An unwritable `-o` printed **no report at all**
and exited 2 even for a clean artifact, so the exit code and the report were decided by a
path rather than by the findings. The failure is still a failure (exit 2), but the report
is printed first — the report is the verdict, the picture is not.

**A whitespace-only name drew a blank disc.** A node with the name `"   "` — a name in
the model — rendered identically to an empty one, so the picture showed a node with no
label instead of a node whose label is blank; it draws `?` now. An inverted bbox
(`x0 > x1`, which no tool emits) also stopped raising inside Pillow: the corners are
sorted.

### Attacked and found sound

**Boxes land on their objects**: for all ten scene tools the drawn centroids match
`compute_layout` to ≤ 1.6 px and the rectangles equal `node_box(pos, r) ± pad` /
`cell_box(cell)`; `chartgx`'s `origin="bottom-left"` flip is correct (display-y boxes land
on the right raster rows); `framegx`'s frozen-run union is correct. **Numbers match the
printed list**: box numbers track `Report.sorted()` through mixed severities, and a
finding with no bbox still consumes its number (netgx `dangling-edge` [1] draws no box
while boxes `(2,) (3,) (4,)` follow). **The picture agrees with the claimed counts**:
module/table/role counts, levelgx hazard/item/goal/spawn tiles, and docgx's 5-blocks→5-bands
all measured equal to the model. **Determinism and independence**: `to_image` twice, a
fresh load, and `annotate` twice are byte-identical for all ten tools; rendering never
mutates the model; `--no-storyboard` leaves the report and the exit code unchanged. **Text**
(`<`, `&`, `"`, newline/CR/tab, a 300-character word, emoji) never crashes and is drawn
literally or truncated with `…` — measured, `😀` draws a tofu glyph (font coverage, not a
contradiction), and a 1×1 canvas, 0/1/500 elements, a whole-canvas box, a 1-px box and
`NaN`/`inf` bboxes all render without raising.

### Recorded limit

A node or an edge can still *touch* a canvas edge (a 1-px stroke at the border) for an
extreme layout; the measurement above is that no *self-loop* leaves the canvas, which is
the case that was reported and fixed.
