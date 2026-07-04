# friday/ethics — cross-scope HANDOFF

From: **W-ethics** (branch `friday/ethics`). These changes live OUTSIDE the ethics workstream's
edit scope, so they are written here for the owning workstream to apply. Nothing here is required
for the ethics card to work AI-off/deterministically on desktop or mobile — the flagship is
self-contained. These are polish/retirement items.

---

## → W1 (desktop shell / menu — `qt/aqt/cfa.py`) — RETIRE the one-passage menu action

INCREMENT 4. There must be ONE ethics feature. The minimal-pairs deck (`CFA::Ethics Pairs`) is now
the single seeded + bundled ethics deck. Remove the "Study Ethics (One-Passage)" action so the
one-passage flagship is no longer exposed.

**Exact change in `qt/aqt/cfa.py`:** delete these two lines from `build_cfa_menu` (currently lines
62–63):

```python
    passages = menu.addAction("Study Ethics (One-Passage)")
    qconnect(passages.triggered, lambda: study_ethics_passages(mw))
```

Then the now-unused `study_ethics_passages(mw)` function (currently starting ~line 215) can be
deleted, or kept but marked deprecated (it is only referenced by the deleted menu line). If it is
kept, add a leading comment: `# DEPRECATED (friday/ethics INC4): one-passage retired; minimal-pairs
is the single ethics flagship. Not wired into the menu.` The `ETHICS_PASSAGES_DECK_NAME` constant
can stay (harmless) or be removed with the function.

`qt/tests/test_cfa_menu.py` asserts the menu's actions — after removing the action, update that test
so it no longer expects "Study Ethics (One-Passage)" (it should still expect "Study Ethics
Minimal-Pairs"). That test file is out of the ethics scope too, so it is W1's to update.

The "Study Ethics Minimal-Pairs" action (`study_ethics_pairs`, filters to `CFA::Ethics Pairs`) is
the single ethics entry point and needs no change.

---

## → W1 or bridge owner (`qt/aqt/cfa_ethics_ai.py`) — OPTIONAL provenance passthrough

INCREMENT 2. The pairs card sends the SAME `cfaGradeEthics:` payload shape the one-passage card
sends, so **no change is required** — the bridge already grades it and returns
`{source, grade, verdict_correct, correct, explanation, per_span, error, model}`.

`ai_grading.grade_semantic` / `grade_fallback` now ALSO return `standard` + `item_id` (echoed from
the payload) so the card can render the named governing Standard in the AI-feedback block. The
bridge passes the payload through unchanged, so these already flow to the card **as long as the card
includes `standard` + `itemId` in the payload it sends** (it does — see the pairs `front.html`
`requestAiGrade`). No bridge edit needed for provenance; this note is FYI.

If the bridge owner wants to *enforce* the AI master/grading toggles server-side (col.conf keys
`cfa_ai_enabled` + `cfa_ai_grading_enabled`): gate `handle_grade_request` so it returns the
deterministic fallback (`grade_fallback(...)` with `error="ai_disabled"`) when either toggle is
absent/false, before calling `grade_semantic`. The card already degrades gracefully (it only shows
the AI block when `resp.source === "ai"`), so this is defense-in-depth, not required for correctness.

---

## → W5 (persistence / `card.custom_data` via the bridge) — attempt-detail payload shape

INCREMENT 5. The pairs card emits a structured attempt-detail payload on every completed attempt,
both to `localStorage["cfaEthics:pending"]` and (unchanged) via `pycmd("ans")` / `pycmd("ease3|1")`.
W5 should read this payload (e.g. in a `webview_did_receive_js_message` handler or by reading the
localStorage relay the back template already consumes) and persist it into `card.custom_data` (which
syncs). Do NOT block review on it; it is additive telemetry.

**Exact payload shape** (JSON object, `localStorage["cfaEthics:pending"]`, set the moment the front
reveals the grade — see the pairs `front.html` `reveal()`):

```jsonc
{
  "pairId": "SMD-01",          // note PairId (stable id of the item)
  "itemId": "SMD-01",          // alias of pairId, for parity with the one-passage payload
  "cluster": "cluster::suitability-mnpi-diligence",
  "completed": true,           // gate: back only honors a completed attempt for this card
  "correct": true,             // overall deterministic grade (both verdicts right AND highlight "correct")
  "standard": "II(A) Material Nonpublic Information",  // named governing Standard
  "source": "fallback",        // "ai" once the AI feedback returns, else "fallback" (deterministic)
  "verdicts": {                // per-case conform/violate verdict + correctness
    "A": {"judged": "violate", "answer": "violate", "ok": true},
    "B": {"judged": "conform", "answer": "conform", "ok": true}
  },
  "decisiveCase": "A",         // which vignette holds the decisive (violating) spans
  "highlight": "correct",      // multi-span grade tier: correct|somewhat|partial|wrong
  "found": 2,                  // # gold spans FULLY covered
  "near": 0,                   // # gold spans NEAR-matched (materially overlapping)
  "total": 2,                  // # gold spans authored on the violating vignette
  "selectionIndices": [24,25,26,27,28,42,43,44,45,46,47,48,49,50], // union of token indices highlighted in the decisive vignette
  "spans": [                   // per-span detail (token index range within the decisive vignette)
    {
      "phrase": "exact unreleased quarterly earnings figure",
      "rationale": "…why this is the MNPI…",
      "tier": "full",          // full|near|none
      "matched": true,         // tier !== "none"
      "lo": 24, "hi": 28       // inclusive token-index range of the GOLD span (decisive vignette)
    },
    { "phrase": "sells the company out of her clients' portfolios", "rationale": "…", "tier": "full", "matched": true, "lo": 42, "hi": 50 }
  ]
}
```

Notes for W5:
- Token indices are into the **decisive vignette** tokenized by the shared `cfaTokenize` (whitespace
  split). They are stable for a given item's authored text.
- The `source` field is `"fallback"` at reveal time and is upgraded to `"ai"` in-place if/when the
  desktop AI bridge returns an `ai` grade (the card re-persists the payload with `source:"ai"` and
  the AI per-span notes). If you snapshot at `pycmd("ans")` time you'll usually get `"fallback"`
  (the AI call is async); snapshotting from the localStorage value the back reads is fine either way.
- Suggested `custom_data` key namespace: `{"cfaEthics": { …the object above… }}`. Keep it small;
  `custom_data` is size-limited and syncs.

---

## → e2e owner (`ts/tests/e2e/ethics_pairs_flow.test.ts`) — update to the multi-span flow

INCREMENT 1. The minimal-pair card is now a MULTI-SPAN highlight (the learner highlights EVERY
decisive span in the violating vignette, graded with partial-credit tiers), not a single contiguous
phrase. The existing Playwright e2e test highlights only the single `decisive_phrase` and asserts
"Fully correct"; under multi-span that is now a *partial* grade (1 of N spans), so the test needs a
small update. `just build` (this workstream's per-increment gate) does NOT run e2e — the e2e suite
runs via `just test-e2e` — so this does not block the flagship, but the test should be brought in
line. `ts/tests/e2e/` is outside the ethics edit scope, hence this handoff.

Exact changes in `ts/tests/e2e/ethics_pairs_flow.test.ts`:
- The card now reads a `GoldSpans` field (JSON `[{phrase, rationale}]`); add it to the `fields` map
  in `renderFront` (parse from `pair.gold_spans`, JSON-stringify into `{{GoldSpans}}`), OR leave it
  empty to exercise the legacy single-phrase fallback. To test the real flagship, pass the real
  `gold_spans`.
- Instead of highlighting only `decisive_phrase`, highlight EVERY gold span: for each
  `pair.gold_spans[k].phrase`, compute its `findGoldIndices` run in the violating vignette and
  tap first+last word (the same tap-first/tap-last commits one span each).
- The painted-selection class is still `.cfa-tok.sel` (unchanged), so the `toHaveCount` assertion
  should sum the token counts of ALL highlighted spans.
- After Check, the reveal still contains `pair.standard` and "Fully correct" once every span is
  highlighted with the correct verdicts; it also now contains "Decisive phrases: N of N found".
  `pair.decisive_phrase` is still shown (it is covered by the gold spans), so that assertion holds.

A minimal, correct replacement test body is available from the pairs `front.html` reveal contract;
the token-locator helpers already in the file (`findGoldIndices`) are sufficient — just loop over
`pair.gold_spans`.

## Status of handoffs
- [ ] W1: remove "Study Ethics (One-Passage)" menu action + update `qt/tests/test_cfa_menu.py`.
- [ ] W1/bridge: (optional) enforce AI toggles in `handle_grade_request`.
- [ ] W5: persist the attempt-detail payload into `card.custom_data`.
- [ ] e2e owner: update `ts/tests/e2e/ethics_pairs_flow.test.ts` to the multi-span highlight flow.
