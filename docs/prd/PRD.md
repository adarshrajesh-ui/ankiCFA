# Speedrun PRD — INDEX (root map; do not inline sub-specs here)

**Project:** Desktop + mobile study app forked from Anki for ONE graduate exam.
**Exam:** TBD (MCAT | USMLE Step 1 | GMAT | LSAT) — decide AM. Build exam-agnostic until then.
**License:** AGPL-3.0-or-later, credit Anki.

## How agents use this PRD (READ THIS)
- Read THIS index for the map + shared contracts only. Then read ONLY your assigned leaf.
- Do NOT read other leaves unless a contract below points you to one.
- Do NOT edit this INDEX. Edit only your own leaf file. Keep each leaf < 900 words,
  self-contained: Scope / Out-of-scope / Interfaces (in/out) / Done-check.

## Architecture (shared engine)
proto/ (contract) → codegen → rslib/ (Rust core: scheduler/collection/sync) →
pylib/ (PyO3 bridge) → Python API → qt/ (desktop). Mobile = AnkiDroid over the same
Rust backend via FFI/rsdroid. Our Rust change ships to BOTH platforms.

## Leaves (scope → path → owner → status)
- Desktop build + Rust "mastery query" chanp-rust.md → agent-1 → WIP
- Mobile (AnkiDroid) build + review loop → docs/prd/mobile-build.md → agent-2 → WIP
- Honest scoring layer (Memory/Performance/Readiness + give-up) → docs/prd/scoring.md → agent-3 → WIP
- Shared-engine wiring research (scout) → docs/prd/shared-engine.md → firstmate → WIP

## Shared contracts (the only cross-agent coupling)
- Rust mastery query returns per-topic {mastered_count, avg_recall}; Python-callable.
- Scoring layer consumes ReviewRecord{card_id,topic,ts,grade,latency,was_new} — it does NOT
  depend on Anki building (uses synthetic fixtures now; wires to real data later).
- Every score object: {point, range, coverage_pct, confidence, updated_at, reasons, abstain}.
- Give-up rule (default): abstain if graded_reviews < 200 OR coverage < 50%.
