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
| `framegx` | `frozen` means the picture does not change; `all-black` means nothing was drawn | a real moving clip; a still clip encoded as video; an all-black clip; a clip changed for one frame | correct, and the discriminating case holds: **one changed frame is not `frozen`** (the claim needs ~1.5 s of sameness), and real motion is clean |
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
