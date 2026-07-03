# P1 desktop fixes — notes

## item1 — "Study Ethics Minimal-Pairs" dead-ends with a false "not available in this build" modal

### Symptom

CFA menu → **Study Ethics Minimal-Pairs** dead-ended on a _repeat_ invocation with a
"No cards to study" tooltip and a false modal — _"The CFA::Ethics Pairs deck is not
available in this build, so there is nothing to study yet."_ — even though the 30
shipped ethics cards clearly exist.

### Root cause

`_study_filtered_deck` (qt/aqt/cfa.py) always called
`col.sched.get_or_create_filtered_deck(deck_id=DeckId(0))`, i.e. it always created a
**brand-new** filtered deck named `CFA::Study — Ethics Minimal-Pairs`. On a repeat
invocation a leftover filtered deck of that same name still held the 30 cards from the
previous build. Anki will not gather cards that already live inside a filtered deck, so
the new build gathered **0** cards → `SearchReturnedNoCards` (`FilteredDeckError`) → the
"No cards to study" tooltip → `study_ethics_pairs` seeded/retried, still gathered 0
(cards still stuck in the leftover deck) → surfaced the false "not available in this
build" modal.

### Fix (additive, backward-compatible; qt/aqt/cfa.py only)

1. `_study_filtered_deck`: before building, look up an existing filtered deck of the same
   name (`col.decks.id_for_name(name)` + `col.decks.is_filtered(...)`) and, if present,
   pass its id to `get_or_create_filtered_deck`. `add_or_update_filtered_deck` then
   **rebuilds it in place**: it returns the current cards home first, then re-gathers them
   via the search — so the action reliably re-enters review on every invocation. (The
   helper is shared with "Study by Exam Priority", so the fix is generic.)
2. `study_ethics_pairs`: the "not available in this build" modal can now **never** fire
   when the ethics deck/cards actually exist — if a study attempt still fails but the
   `CFA::Ethics Pairs` deck has cards, we show an honest tooltip instead of the false
   claim.
3. Made the touched file fully mypy-clean (pre-existing errors only): `# type: ignore[arg-type]`
   on the protobuf `SearchTerm(order=...)` enum arg (matches the repo's own convention in
   `qt/aqt/filtered_deck.py`) and renamed a loop var that shadowed the `Collection` in
   `ExamReadinessDialog`.

### Regression test (fails without the fix, passes with it)

`qt/tests/test_cfa_f0b.py::test_study_ethics_pairs_is_reentrant_no_false_modal`
Seeds the 30 ethics cards, invokes `study_ethics_pairs` twice, and asserts the second
invocation re-enters review with the 30 cards AND that the false modal never fires.

### Before / after proof

- `proof/fixes/p1/item1-before.txt` — symptom probe (call #2 does not re-enter review;
  false modal fires; source deck still has 30 cards) + regression test FAILING.
- `proof/fixes/p1/item1-after.txt` — same probe now re-enters review on calls #2 and #3
  with no modal + regression test PASSING.
- `proof/fixes/p1/item1-verify.txt` — full regression battery (see below).

### Tests run (raw pytest against the single `just build`; results)

- `qt/tests/test_cfa_f0b.py` — **6 passed** (incl. new regression test)
- `qt/tests/test_cfa_menu.py` — **3 passed**
- `qt/tests/test_cfa_f5_style.py` — **13 passed**
- `pylib/tests/test_cfa_scores.py` — **10 passed**
- `pylib/tests/test_cfa_f4.py` — **14 passed**
- `qt/tests/test_cfa_f4_dialog.py` — **3 passed**
- F9 reachability (AI-OFF, the honest default) — **F9 REACHABILITY: PASS**
- mypy on `qt/aqt/cfa.py` (`.mypy.ini`) — **Success: no issues found** (was 3 pre-existing errors)
- ruff check + ruff format --check on touched files — **clean**

Note: F9 must be run AI-OFF (its designed default: "no OPENAI_API_KEY is required"). This
environment has a gitignored `.env` key that auto-loads, so F9 was run with the key
neutralized (`OPENAI_API_KEY=""`, never printed); it then prints `F9 REACHABILITY: PASS`.

### Branch / commit / no-mistakes / merge

- Branch: `fix/desktop-item1` (off `origin/main`).
- Fix commit SHA: `b03d3467e` (scoped: `qt/aqt/cfa.py`, `qt/tests/test_cfa_f0b.py`, `proof/fixes/p1/`).
- no-mistakes gate had to be repaired first: pushes were failing with
  `push_received error="invalid gate path: ."` (a broken gate hook that had blocked
  every branch for ~2 days). `no-mistakes init` refreshed the gate/hook and fixed it;
  a delete + re-push then triggered the run.
- no-mistakes outcome: **checks-passed** — all steps 0 findings
  (intent skipped[author-mismatch] · rebase · review · test · document · lint · push · pr · ci green).
  Run id `01KWMKA4Z54HN3VB45QCE9H8MQ`.
- The no-mistakes **document** step auto-added commit `afdc1658` — a 2-line
  `SUBMISSION-CHECKLIST.md` sync (F0b test count 5 → 6) reflecting the new regression
  test. This is a gate-produced doc commit, not a manual edit.
- PR: https://github.com/adarshrajesh-ui/ankiCFA/pull/2 (**MERGED**, squash).
- Merge confirmation: `origin/main` advanced `557a7cc82` → **`8213f83a0`**
  ("fix(cfa): re-enter review for Study Ethics Minimal-Pairs and drop false modal (#2)");
  `origin/main:qt/aqt/cfa.py` contains the reuse/rebuild fix.

_(This NOTES finalization was landed via a follow-up gate run from an isolated worktree
so the concurrent agents' live working tree was never disturbed.)_

## item2 — "Study by Exam Priority" dead-ends on a fresh profile with NEW cards

### Symptom

CFA menu → **Study by Exam Priority** dead-ended with a "no studyable cards" modal on a
fresh profile, even though the collection has 20+20 NEW (never-studied) CFA cards. It
should enter the read-only Rust exam-priority queue (`BuildExamQueue`) ordered
weakest-first INCLUDING new cards (treated as maximally weak, R=0), so a fresh profile is
never a dead-end.

### Root cause (confirmed by reproduction, not assumed)

`study_by_exam_priority` (qt/aqt/cfa.py) scoped `build_exam_queue` to the **current** deck
via `col.decks.get_current_id()`. On a fresh profile the first-launch seeder
(`aqt.cfa_seed` → `tools/cfa/seed_collection`) creates the CFA decks but never **selects**
one, so the current deck stays the empty built-in **"Default"** deck. The deck-scoped RPC
therefore returns 0 `card_ids` and the empty-guard shows the modal — even though hundreds
of NEW CFA cards sit in `CFA Level II` / `CFA::Ethics Pairs`.

Item 1's hypothesis ("new cards excluded by the RPC and/or the filtered deck") was **ruled
out empirically**: with a CFA deck selected, the RPC returns the new cards (R=0) and the
filtered deck gathers them, entering review normally. The bug was the deck **scope**, not
new-card exclusion. (See `item2-before.txt` for the mechanism probe.)

### Fix (additive, backward-compatible; pylib/anki/cfa.py + qt/aqt/cfa.py; NO rslib changes)

1. `pylib/anki/cfa.py`: add `ExamQueue` (a small result type) and
   `build_exam_queue_all_decks`, which calls the existing read-only `build_exam_queue` once
   per **top-level** deck (each with its subdecks, so every studyable card is scored exactly
   once) and merges the per-deck results into one weakest-first ordering (score desc, ties by
   ascending card id — matching the RPC), including NEW cards.
2. `qt/aqt/cfa.py` `study_by_exam_priority`: when the current-deck queue is empty, fall back
   to `build_exam_queue_all_decks` so the collection's NEW cards are reached and review is
   entered; the honest count (including new) is still reported.
3. Gate refinement (no-mistakes review step, commit `2954d71b`): the collection-wide fallback
   is **gated to the built-in "Default" deck** (`deck_id == DEFAULT_DECK_ID`) so it only
   bootstraps a fresh profile and never silently hijacks a user who deliberately selected and
   then finished a specific non-Default deck; that case now shows a deck-scoped "switch decks"
   modal. A matching regression test was added by the gate.

### Regression tests (fail without the fix, pass with it)

- `qt/tests/test_cfa_f0b.py::test_study_by_exam_priority_from_empty_default_deck_no_dead_end`
  — a freshly seeded all-NEW profile whose current deck is the empty Default deck now enters
  a non-empty weakest-first exam-priority review and populates the filtered study deck (30
  cards), with no dead-end modal.
- `qt/tests/test_cfa_f0b.py::test_study_by_exam_priority_non_default_empty_deck_does_not_hijack`
  (added by the gate) — a deliberately-selected empty non-Default deck is NOT hijacked into the
  collection-wide queue; it surfaces a deck-scoped modal instead.
- `pylib/tests/test_cfa.py::test_build_exam_queue_all_decks_merges_new_cards_across_decks`
  — `build_exam_queue_all_decks` merges NEW cards across two sibling top-level decks
  weakest-first (higher-weight topic first) and honors `fetch_limit`, while a deck-scoped
  queue on the empty Default deck is empty.

### Before / after proof

- `proof/fixes/p1/item2-before.txt` — faithful `study_by_exam_priority` reproduction
  (scenario A: current deck = Default → DEAD-END) + the mechanism probe (RPC + filtered
  gather DO include new cards when a CFA deck is selected) + both new regression tests
  FAILING against origin/main source.
- `proof/fixes/p1/item2-after.txt` — the same reproduction now ENTERS REVIEW (200 cards,
  200 new) + both regression tests PASSING.
- `proof/fixes/p1/item2-verify.txt` — the full regression battery (below).

### Tests run (raw pytest against the single `just build`; results)

- `qt/tests/test_cfa_f0b.py` — **8 passed** (incl. 2 new regression tests)
- `qt/tests/test_cfa_menu.py` — **3 passed**
- `pylib/tests/test_cfa.py` — **10 passed** (incl. new merge test)
- `pylib/tests/test_cfa_scores.py` — **10 passed**
- `pylib/tests/test_cfa_f4.py` — **14 passed**
- `qt/tests/test_cfa_f4_dialog.py` — **3 passed**
- `qt/tests/test_cfa_f5_style.py` — **13 passed**
- F9 reachability (AI-OFF, key neutralized via `env -u OPENAI_API_KEY`) — **F9 REACHABILITY: PASS**
- mypy on `pylib/anki/cfa.py qt/aqt/cfa.py` (`.mypy.ini`) — **Success: no issues found in 2 source files**
- ruff check + ruff format --check on touched files — **clean**

### Branch / commit / no-mistakes / merge

- Worktree: `/Users/adarshrajesh/AlphaWeek2/ankicfa-wt-item2` (branch `fix/desktop-item2` off
  `origin/main` @ `efb9fabd2`), to avoid disturbing the concurrent agents' live main tree.
- Fix commit SHA: `d3cdf787e` (scoped: `pylib/anki/cfa.py`, `qt/aqt/cfa.py`,
  `pylib/tests/test_cfa.py`, `qt/tests/test_cfa_f0b.py`, `proof/fixes/p1/`).
- no-mistakes outcome: **checks-passed** (CI green), run id `01KWMNJQXK4C5PB53H8THCX637`
  (intent skipped · rebase · review · test · document · lint · push · pr · ci green).
- Gate-produced fixes (all reviewed, in-scope, honest):
  - review `2954d71b` — gate the fallback to the Default deck + expand a docstring (see above),
    with an added regression test.
  - document `94c17a3f` — trivial doc syncs: `SUBMISSION-CHECKLIST.md` F0b 6 → 8,
    `docs/cfa/UPSTREAM_FILES.md` test count 7 → 10, and a `study_by_exam_priority` docstring
    note. (No substantive README/Brainlift edits.)
  - document `5c0b4b81` — regenerated the `item2-*.txt` proof battery for the 8-test F0b count
    (independently re-verified: F0b 8, test_cfa 10, F9 PASS, mypy clean).
- PR: https://github.com/adarshrajesh-ui/ankiCFA/pull/4 (**MERGED**, squash).
- Merge confirmation: `origin/main` advanced `efb9fabd2` → **`442d69c25`**
  ("fix(cfa): fall back to collection-wide exam-priority queue on empty Default deck (#4)");
  `origin/main:pylib/anki/cfa.py` has `build_exam_queue_all_decks` and
  `origin/main:qt/aqt/cfa.py` has the `on_default_deck` fallback.

_(This item2 NOTES entry was landed via a follow-up gate run from the isolated worktree so
the concurrent agents' live working tree was never disturbed.)_
