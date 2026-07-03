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

## item3 — Exam Readiness hero over-claims below the give-up threshold, and topic accounting is deck-fragmented

Two independent sub-bugs in the **Exam Readiness** dialog.

### Sub-bug 3A — the hero must ABSTAIN below the give-up threshold

#### Symptom

On a fresh/lightly-studied deck the dialog printed a confident headline —
_"likely fail **p=0.07**"_ (or "likely pass"), with an "Estimated exam accuracy … (95% CI …)"
lead line — while the three honest scores directly beneath it (Memory, Performance,
Readiness) all correctly said _"Not enough data"_. The confident call came entirely from
the flat Beta(1,1) prior, not from evidence.

#### Root cause

`_readiness_call_html(r)` (qt/aqt/cfa.py) always rendered `cfa_style.hero(call=…, call_prob=…)`,
which always prints `p=…`. `bayesian_readiness()` never abstains (by design — the band is
just wide with little data), so the UI showed a verdict even with 2 graded reviews.

#### Fix (additive, backward-compatible; qt/aqt/cfa.py only — no cfa_style.py edits)

The dialog already computes `score = cfa.memory_score(col, deck_id)`. It now uses
`score.abstain` (which enforces the give-up thresholds — `MIN_GRADED_REVIEWS=200`,
`MIN_TOPIC_COVERAGE=0.50`, plus the high-weight-topic-skip rule) as the trigger:

- Below the threshold → a new **inline** abstain hero, `_readiness_abstain_html(reason)`,
  composed by hand (deliberately NOT via `cfa_style.hero`) so it prints **no `p=`** and
  **no accuracy "95% CI"** lead — just _"Not enough data — keep studying"_, the give-up
  reason, and the standing "not validated" caveat. It reuses cfa_style's public
  tokens/helpers read-only (`WARN`, `TOKENS`, `INK`, `value_abstain`) so it keeps the
  shared chrome.
- Above the threshold → unchanged behaviour (`_readiness_call_html(bayes)` still shows the
  call + 95% CI).

`bayesian_readiness()`'s API is unchanged — it still computes and returns the call; only
the UI suppresses/replaces the hero when abstaining.

### Sub-bug 3B — topic accounting must be canonical + consistent (count == table rows == list)

#### Symptom

The caption showed `{topics_covered}/{topics_total}` while the per-topic table rendered
from `score.topics`, and the totals were **not** pinned to the CFA syllabus: with no exam
config the total varied with the selected deck (e.g. `2` for the parent deck, `1` for a
subdeck) and the coverage denominator was wrong (`coverage 1.000` on a single-topic deck).
Worse, opening the dialog with **no exam config crashed** with
`ValueError: too many values to unpack (expected 3)`.

#### Root cause

`memory_score`/`bayesian_readiness` derived `topic_prefixes = sorted(weights.keys()) if
weights else _derive_topics(rows)`. The `_derive_topics(rows)` fallback:

1. builds a **deck-scoped** list from whatever `los::` tags are in scope → variable totals,
   not the fixed syllabus; and
2. unpacked **3** columns per row, but `bayesian_readiness`'s query selects **4**
   (`id, tags, R, ivl`) → `ValueError` whenever it hit the no-config fallback.

#### Fix (additive, backward-compatible; pylib/anki/cfa.py only)

- New in-code source of truth `CANONICAL_TOPICS` — the **eight authored CFA topics** present
  in `cfa/deck/*.jsonl` (`altinv, corp, econ, equity, ethics, fra, portmgmt, quant`).
  (README's "10" is stale/out-of-scope — the two extra `BASE_TOPIC_WEIGHTS` entries,
  `fixed-income` and `derivatives`, have no authored items.)
- New helper `readiness_topic_prefixes(weights)` = `sorted(weights.keys())` when exam
  weights are configured (the seeded product already persists one weight per authored
  topic → 8), else the canonical list (a fresh copy). Both `memory_score` and
  `bayesian_readiness` now call it; the buggy `_derive_topics` is removed.

Result: `topics_total == len(score.topics)` always, the total is the canonical 8 and
**deck-independent**, the table renders one row per canonical topic (uncovered → "no data"),
caption == table == list, and the no-config crash is gone. The coverage give-up denominator
correctly going `1 → 8` (so a single studied topic is `1/8 < 0.50` → abstains) is the
intended behaviour.

### Regression tests (fail without the fix, pass with it)

- `qt/tests/test_cfa_f4_dialog.py`
  - `test_dialog_hero_abstains_below_giveup_threshold` — **inverts** the old
    `test_dialog_renders_with_almost_no_data_no_giveup_wall`: with 2 reviews the hero must
    now abstain ("keep studying", no `p=`, no "95% CI"); caveat retained.
  - `test_dialog_hero_shows_call_above_giveup_threshold` — the complement: with enough
    evidence the confident call (`p=`, "95% CI") is still shown and the abstain hero absent.
  - `test_dialog_topic_count_is_canonical_and_consistent` — no config → table rows ==
    "/8 topics" caption == `len(score.topics)` == 8, and the dialog renders (no crash).
  - `test_readiness_abstain_html_pure` — the inline abstain hero: "keep studying", no `p=`,
    no "95% CI", surfaces the reason + caveat.
- `pylib/tests/test_cfa_f4.py` — `CANONICAL_TOPICS` shape; `readiness_topic_prefixes`
  config-vs-fallback; `bayesian_readiness` no-config uses canonical 8 & never crashes;
  topic total deck-independent; full-canonical config totals 8.
- `pylib/tests/test_cfa.py` — `memory_score` no-config canonical total; partial-study
  covered count + `1/8` denominator → abstain; deck-independence; configured total.

The existing pylib API tests (`test_readiness_never_abstains_and_is_wide_with_little_data`,
`test_uncovered_high_weight_topic_widens_band_without_abstaining`, etc.) stay green
**unchanged** — they configure exam weights, so they use the `sorted(weights.keys())` path
and keep asserting the pylib fn still returns a call.

### Before / after proof

- `proof/fixes/p1/item3_repro.py` — offscreen-Qt + real-Collection harness (prints
  per-check `VERDICT: OK/BUG`).
- `proof/fixes/p1/item3-before.txt` — 3A hero is CONFIDENT (`p=`, "likely", "95% CI") while
  all three scores abstain; 3B totals vary (2 vs 1), wrong denominator, and
  `bayesian_readiness`/dialog crash with `ValueError`.
- `proof/fixes/p1/item3-after.txt` — 3A hero ABSTAINS ("keep studying", no `p=`/CI); 3B
  total == 8 deck-independent, coverage `/8`, dialog renders, all `VERDICT: OK (fixed)`.
- `proof/fixes/p1/item3-verify.txt` — full regression battery (below).

### Tests run (raw pytest against the single `just build`; results)

- `pylib/tests/test_cfa_f4.py` + `test_cfa_scores.py` + `test_cfa.py` — **43 passed**
  (19 + 10 + 14; +5 and +4 new).
- `qt/tests/test_cfa_f4_dialog.py` + `test_cfa_f5_style.py` + `test_cfa_menu.py` —
  **22 passed** (6 + 13 + 3; dialog +3 new incl. the inverted test).
- `qt/tests/test_cfa_f0b.py` — **8 passed**.
- Broader sweep (all CFA suites) — **62 pylib + 55 qt passed**.
- F9 reachability (AI-OFF, `OPENAI_API_KEY` neutralized, never printed) —
  **F9 REACHABILITY: PASS** (`F4 readiness: call=likely fail p_pass=0.07` — the pylib fn
  still returns a call; only the UI abstains).
- mypy on `pylib/anki/cfa.py` + `qt/aqt/cfa.py` — **Success: no issues found in 2 source files**.

### Branch / commit (NO no-mistakes, NO push, NO merge — per task)

- Branch: `fix/desktop-item3b` (off `origin/main`), isolated worktree
  `ankicfa-wt-item3b`.
- Scope (edited): `pylib/anki/cfa.py`, `qt/aqt/cfa.py`, `pylib/tests/test_cfa.py`,
  `pylib/tests/test_cfa_f4.py`, `qt/tests/test_cfa_f4_dialog.py`, `proof/fixes/p1/`.
- Committed as a single commit on `fix/desktop-item3b`. Deliberately **not** pushed, **not**
  run through no-mistakes, and **not** merged — this attempt is one half of a best-of-N pair
  left for finalization.
