# friday/ethics — minimal-pairs is the single graded ethics flagship

Workstream owner: **ethics** (W-ethics). Branch: `friday/ethics` (off `origin/main` HEAD `6ef32ec8c`).

Mission: make the **two-passage minimal-pairs** card the SINGLE ethics flagship — polished, graded
(multi-span highlight + partial-credit tiers + named governing Standard + AI grading with
deterministic fallback), shipped to BOTH desktop first-run AND the mobile bootstrap `.apkg`. Retire
the one-passage duplication. Keep Python<->JS grader parity byte-for-byte.

## Decisions / conventions (autonomous)
- **Multi-span on the violating vignette.** The learner highlights EVERY decisive span in the
  vignette that is a *violation* (not one contiguous phrase). Grading reuses the one-passage
  `grade_spans_tolerant` / `span_tier` (partial-credit tiers: correct / somewhat / partial / wrong),
  with the same `SPAN_CAP_SLACK = 4` and half-overlap "near" threshold. The shared block in the
  pairs `front.html` is the multi-span `CFA-SPAN-SHARED` block (mirrored to
  `tests/js/passage_logic.js` + `ethics_scoring.py`), so there is now ONE shared grader for both.
- **Additive schema.** `pairs.jsonl` keeps the legacy `decisive_phrase` / `decisive_fact` /
  `decisive_phrase_case` fields (importer round-trip + validators stay valid) and ADDS a
  `gold_spans: [{phrase, rationale}]` array on the violating vignette. When `gold_spans` is absent
  the importer/validator derives a single-span `[{phrase: decisive_phrase, rationale: rationale}]`
  from the legacy fields, so old banks still work.
- **Provenance.** `ai_grading.grade_semantic` result now also carries `standard` + `item_id` so the
  card can render "Graded by AI · II(A) Material Nonpublic Information". Fallback carries them too.
- **Reused desktop bridge.** The pairs card sends the SAME `cfaGradeEthics:` payload shape the
  one-passage card sends (`passage` = the violating vignette text), so the out-of-scope desktop
  bridge `qt/aqt/cfa_ethics_ai.py` needs NO change. See HANDOFF.md for the (optional) provenance
  passthrough note.

## Increment log
(Each increment: item, commit SHA, before/after evidence paths, tests added, PR link, handoffs.)

**PR:** https://github.com/adarshrajesh-ui/ankiCFA/pull/23

> ⚠️ Shared-tree hazard: this repo working dir is shared with other Friday workstreams; a concurrent
> agent `git checkout`-ed other branches mid-run and my INC1 commit briefly landed on
> `friday/desktop-shell`. I moved it to `friday/ethics` (db6994487) and restored `friday/desktop-shell`
> to origin/main. I now verify `git branch --show-current == friday/ethics` before every commit/push.

### INC1 — multi-span + partial-credit on the minimal-pairs flagship
- **Commit:** `db6994487`
- **Gap (before):** the pairs card graded ONE contiguous `decisive_phrase` via `grade_highlight`
  (breakdown said "Decisive phrase" singular; instruction "Highlight the phrase"). No multi-span, no
  partial-credit tiers. Evidence: `item1-before-front.png`, `item1-before-attempt.png` (a full
  driven attempt showing the single-phrase reveal).
- **Fix (after):** the learner highlights EVERY decisive span in the violating vignette; graded
  correct/somewhat/partial/wrong by the shared multi-span tolerant grader (SAME block as one-passage,
  byte-identical to `tests/js/passage_logic.js`). Reveal shows per-span tiers, "N of N found", named
  governing Standard + per-span rationale. Evidence: `item1-after-front.png`,
  `item1-after-attempt.png` (2-of-2 → Fully correct), `item1-after-partial.png` (1-of-3 → Partial).
- **Files:** `pairs.jsonl` (+`gold_spans` on all 30, additive; legacy fields kept),
  `ethics_notetype.py` (+`GoldSpans` field), `import_pairs.py` (`gold_spans_for` + multi-span
  validation + populate GoldSpans), `templates/front.html` (multi-span CFA-SPAN grader + reveal),
  `templates/back.html` (richer reveal), `tools/cfa/render_pairs_attempt.py` (proof driver).
- **Tests added:** `test_highlight.py` — `test_all_30_pairs_have_multi_span_gold_key_on_violating_vignette`,
  `test_partial_highlight_of_multi_span_pair_is_partial_not_wrong`,
  `test_pairs_front_span_block_matches_passage_logic_js`,
  `test_python_js_multispan_grader_agree_for_pairs`, `gold_spans_for` + validation tests;
  `test_import_pairs.py` — GoldSpans round-trip. All fail without the change (new fields/logic).
- **Verification:** `just cfa-test` 107 passed · `just cfa-validate` ok · `just cfa-passages-test`
  40 passed · `just build` green · ruff clean.
- **Handoffs:** e2e test update (`ts/tests/e2e/ethics_pairs_flow.test.ts`) → HANDOFF.md.

### INC2 — AI semantic grade + provenance wired into the pairs card
- **Commit:** `<INC2_SHA>`
- **Gap (before):** `ai_grading.grade_semantic`/`grade_fallback` results carried no `standard`/
  `item_id`, so the card could not render "Graded by AI · II(A) …" from the grader's provenance.
  Evidence: `item2-before-noai.png` (deterministic reveal, no AI block).
- **Fix (after):** `ai_grading.py` now takes + echoes `item_id` + `standard` on BOTH the AI and
  fallback paths (stable schema; empty strings when unsupplied; the Standard is NEVER put in the
  prompt). The pairs `front.html` already (INC1) calls `pycmd("cfaGradeEthics:" + payload)` with the
  SAME shape the one-passage card sends (`passage` = the violating vignette, plus `itemId`+`standard`),
  so the OUT-OF-SCOPE desktop bridge needs NO change; the card renders the named source in an
  AI-feedback block and keeps its deterministic grade so AI-off / AnkiDroid lose nothing.
  Evidence: `item2-after-ai.png` ("AI FEEDBACK · Graded by AI · II(A) Material Nonpublic
  Information", semantic grade + per-span AI notes, below the deterministic reveal).
- **Files:** `ai_grading.py` (provenance kwargs), `tests/test_ai_grading.py` (+4 provenance tests),
  `templates/front.html` (already sends payload + renders block — from INC1).
- **Tests added:** `test_fallback_carries_item_id_and_standard`,
  `test_ai_path_carries_item_id_and_standard`, `test_provenance_defaults_are_empty_strings_not_missing`,
  `test_standard_never_leaks_into_prompt_but_flows_to_result` (all fail without the new keys).
- **Verification (AI-off, `.env` moved aside per HARD RULE 3):** `just cfa-ai-grade-test` 24 passed
  (17 grader + 7 desktop bridge) · `just cfa-ethics-eval` AI-off baseline 0.733, LLM assertion
  SKIPPED. **With the real key:** `just cfa-ethics-eval` LLM agreement **0.933 ≥ 0.80 PASS** (vs
  0.733 fallback). Key never printed; `.env` always restored. `just build` green · ruff clean.
  NOTE: `qt/tests/test_cfa_ethics_ai.py` asserts AI-off, so it only passes with `.env` moved aside
  (the real key makes it grade `source:ai`) — this is the documented HARD-RULE-3 discipline, not a
  regression; that test is out of scope.
- **Handoffs:** optional 2-line bridge change to forward `itemId`/`standard` into `grade_semantic`
  → HANDOFF.md (card already degrades gracefully without it).
