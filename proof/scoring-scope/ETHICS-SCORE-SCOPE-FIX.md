# Desktop↔phone parity: the special ethics deck now impacts the scores

**Surface:** CFA Home dashboard, Concept Map, native Exam Readiness (desktop)
**Severity:** High — silent correctness / cross-device parity defect on the
objective's most-emphasised requirement ("the special ethics cards … must
impact the readiness score … the concept map").

## The defect

The ethics minimal-pairs bank lives in the **`CFA::Ethics Pairs`** deck — a
*sibling* of the **`CFA Level II`** deck, not a child of it (`import_pairs.py`
puts it there deliberately). The desktop scored the headline numbers with:

```python
deck_id = _cfa_home_deck_id(col)          # -> the "CFA Level II" deck id
payload = _cfa_exam_readiness_payload(col, deck_id)   # scopes to that subtree
```

`memory_score`/`readiness_score`/etc. scope to `deck_and_child_ids(deck_id)`, and
`CFA::Ethics Pairs` is **not** under `CFA Level II`, so **every ethics-pair review
was excluded** from the desktop's three scores, the Bayesian verdict and the
concept-map fills.

Meanwhile the AnkiDroid client already scored the whole collection
(`computeCfaScores(wholeCollection = true)`), so *the same reviews produced
different numbers on desktop vs phone* — a direct violation of "a review on the
phone appears on the desktop and vice-versa."

The native Readiness state was additionally scoped to
`col.decks.get_current_id()` — whichever single deck happened to be selected —
so it drifted from the Home dashboard.

## The fix (desktop only; brings desktop into parity with the phone)

- `_cfa_exam_readiness_payload(col, deck_id)` now treats `deck_id == 0` as
  **whole-collection** scoring (`scope = deck_id or None`). A real deck id still
  scopes to that one deck (per-deck readiness kept working).
- `_cfa_home_payload` passes `0` → the Home dashboard **and** the Concept Map
  (both fed by `getCfaHomeView`) now score every CFA deck.
- `CfaReadiness.show()` loads `cfa-readiness/0` → the native Readiness report is
  whole-collection, matching Home and the phone (no longer the arbitrary
  current deck).

## Proof (`qt/tests/test_cfa_ethics_scoring_scope.py`, real Collection + RPC engine)

Reviews seeded ONLY in the `CFA::Ethics Pairs` sibling deck (3 cards × 5 reviews):

| scope | caption.gradedReviews | Ethics topic gradedReviews | Ethics covered |
|---|---|---|---|
| whole-collection (`deck_id=0`, the fix) | **15** | **15** | **True** |
| old `CFA Level II` subtree scope | 0 | 0 | False |

`test_home_payload_scores_whole_collection` further proves the Home/Concept-Map
payload reflects the ethics reviews (8/8) while its heading still reads
`CFA Level II` (the exam), not a raw sibling deck name.

`just cfa-desktop-shell-test` → 65 passed. `test_cfa_f4_dialog`/`test_cfa_f5_style`
(per-deck payload with a real deck id) → 19 passed, so the scoped path is intact.
