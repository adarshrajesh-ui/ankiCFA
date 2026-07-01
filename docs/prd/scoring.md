# Scoring Leaf — Honest Measurement Layer (agent-3)

## Scope
Standalone Python package `speedrun_scoring/` that turns study history into three
**separate** scores — **Memory**, **Performance**, **Readiness** — each a **range**,
not a single number, plus a strict **abstain** rule. No dependency on Anki building;
operate on a defined data interface + synthetic fixtures. Deterministic, unit-tested.

## Out-of-scope
Network, AI/LLM calls, real Anki data wiring, UI. (Real-data wiring is later.)

## Data interface (in)
- `ReviewRecord{card_id, topic, ts, grade, latency, was_new}` — `ts` in days,
  `grade` 1..4 (1=again/lapse, 2..4=recalled), `latency` seconds.
- `QuestionResult{topic, difficulty, correct, latency, stem}` — `difficulty` 0..1,
  `stem` optional item text (used by leakage check).
- `SyntheticFixture` generator: deterministic (seeded) reviews + questions with a
  known latent recall process and an intentional paraphrase gap.

## Models (out)
All produce a `Score{point, range, coverage_pct, confidence, updated_at, reasons,
abstain}` (shared contract from INDEX).

1. **MemoryModel** — FSRS-style retrievability `R(t)=(1+f·t/S)^d` (d=-0.5, f=19/81).
   Per-card stability `S` estimated from grade history; `point` recall + interval
   from review-count uncertainty. Calibration harness → reliability curve +
   Brier + log-loss on **held-out** last review per card.
2. **PerformanceModel** — `P(correct on a NEW question)` from topic mastery,
   difficulty, timing, coverage. `point`+`range`. MUST be able to differ from
   memory: exposes the **paraphrase-gap** metric = mean card recall − mean reworded-
   question accuracy over shared topics.
3. **ReadinessModel** — maps performance+coverage to a configurable scale
   (`pass_fail` → P(pass); `scaled` → score in [min,max]). `point`+`range`+
   `confidence`.

## Give-up rule (abstain)
Explicit + configurable. **Default: `graded_reviews < 200` OR `coverage < 50%`
⇒ ABSTAIN.** When abstaining, `point`/`range` are `None` and `reasons` explain why.
Enforced by tests. Thresholds live in `ExamConfig` (exam-agnostic; scale in config).

## Support pieces
- **CoverageMap** — from a placeholder topic-outline file, compute % of exam
  covered (topics with sufficient data / total, optionally weighted).
- **Leakage check** — flag duplicate / near-duplicate items (token Jaccard on
  `stem`) between train/test fixtures.

## Config
`ExamConfig{name, scale_type, scale_min, scale_max, pass_threshold,
min_graded_reviews=200, min_coverage_pct=50.0, paraphrase_transfer}`. Ships both a
`pass_fail` and a `scaled` example. No exam is hardcoded into logic.

## Done-check
`scripts/verify_scoring.sh`:
1. runs `pytest` over models, give-up rule (enforced), coverage map, calibration,
   leakage;
2. runs a headless eval (`python -m speedrun_scoring.eval`) that prints calibration
   (Brier/log-loss) + paraphrase-gap on the fixtures;
3. exits 0 only if all pass.

Docs: `docs/models/{memory,performance,readiness}.md`, each stating the give-up rule.

## Interfaces summary
- Consumes: `ReviewRecord`, `QuestionResult` (above). NO Anki import.
- Produces: `Score` objects (shared contract) + calibration/paraphrase metrics.
