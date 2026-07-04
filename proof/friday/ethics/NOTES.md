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

<!-- entries appended per increment below -->
