# P1 desktop fixes — notes

## item1 — "Study Ethics Minimal-Pairs" dead-ends with a false "not available in this build" modal

### Symptom
CFA menu → **Study Ethics Minimal-Pairs** dead-ended on a *repeat* invocation with a
"No cards to study" tooltip and a false modal — *"The CFA::Ethics Pairs deck is not
available in this build, so there is nothing to study yet."* — even though the 30
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
- Branch: `fix/desktop-item1` (off `origin/main`)
- Commit SHA: _(filled after commit)_
- no-mistakes outcome: _(filled after run)_
- PR: _(filled after run)_
- Merge confirmation (origin/main SHA): _(filled after merge)_
