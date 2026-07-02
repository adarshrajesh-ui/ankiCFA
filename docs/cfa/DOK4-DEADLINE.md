# Deadline retention: peak recall on the exam day (DOK-4)

_One-page design note for the CFA Level II fork. This is a **second**, distinct
read-only Rust engine change, separate from `BuildExamQueue`._

## The thesis

FSRS is built to minimise review cost for **indefinite** retention: it schedules
the next review for roughly when a card is about to drop to your desired
retention, forever. The CFA exam does not want indefinite retention — it wants
**peak retention on ONE date**. Those are different objectives:

- FSRS will happily push a well-known card's next review to a date **after** the
  exam, spending zero effort on it before the day that matters.
- FSRS ranks by "due-ness", not by "how likely am I to recall this **on exam
  day**".

`DeadlineRetention` reframes scheduling around the deadline. For a deck + exam
date it:

1. **predicts each due card's FSRS retrievability at the exam date** — not now,
   but at the exam instant; and
2. **caps the next interval** so the last productive review sits just before the
   exam and no review is ever scheduled past it; then
3. **surfaces the weakest-on-the-day cards first.**

## The naive formula

For each due card in the deck (and subdecks):

```
horizon_secs        = exam_date − now
elapsed_at_exam     = seconds_since_last_review + horizon_secs        (clamped ≥ 0)
predicted_recall    = FSRS.current_retrievability_seconds(
                          memory_state, elapsed_at_exam, decay)        # in [0,1]
suggested_interval  = clamp(days_to_exam, 0, card.interval)           # = min(ivl, days_to_exam), ≥ 0
```

Cards are returned as parallel arrays sorted by `predicted_recall` **ascending**
(weakest first), ties broken by ascending card id for determinism. A card with
no FSRS memory state (never reviewed) is treated as maximally weak
(`predicted_recall = 0`) so it rises to the top.

`predicted_recall` reuses the **exact** helper the rest of the engine and
`BuildExamQueue` use — `FSRS::current_retrievability_seconds` — so the numbers
are identical to what the scheduler and stats already show; the only twist is
advancing the elapsed time out to the exam date.

## How this differs from `BuildExamQueue`

| | `BuildExamQueue` | `DeadlineRetention` (this) |
| --- | --- | --- |
| Question | "What should I study next?" (weighted weakness **now**) | "What will I fail **on exam day**, and when is the last useful review?" |
| Score | `topic_weight × (1 − R_now) × urgency` | `R(exam_date)` + a per-card interval cap |
| Time frame | present retrievability | retrievability **projected to the exam date** |
| Output | `card_ids[] / scores[]` (score desc) | `card_ids[] / predicted_recall[] / suggested_interval_days[]` (recall asc) |
| Suggests intervals | no | **yes** — `min(FSRS interval, days_to_exam)` |

They are complementary, not redundant: one reweights *today's* queue by topic
importance; this one projects recall onto a fixed date and tightens intervals to
land before it.

## Read-only guarantee

Like `BuildExamQueue`, this writes **nothing** — no card, queue, revlog, or
config mutation. It performs one read-only search (`deck:… is:due`), reads each
card's memory state, and returns computed values. FSRS scheduling and the undo
history stay valid; running it never appears on the undo stack. This is verified
by Rust unit tests (`deadline_retention_is_read_only_and_preserves_undo`) and a
Python test (`test_is_read_only_and_adds_no_undo_step`).

## Honest limits (this is deliberately naive)

This is a per-card **cap + reweight**, not an optimal-control solution. In
particular:

- **Not a scheduler.** It suggests a capped interval; it does not (and must not)
  reschedule cards. Adopting a suggestion is a separate, explicit user action.
- **"FSRS interval" = the card's stored interval.** We cap `card.interval`, the
  interval FSRS already assigned, rather than re-deriving a fresh optimal
  interval from stability/desired-retention. Simple and deterministic, but it
  does not re-optimise.
- **No multi-review planning.** `predicted_recall` assumes no further reviews
  between now and the exam. It answers "if I did nothing, where would this card
  be on exam day?" — it does not solve for the optimal *sequence* of reviews
  (spacing, count, ordering) that would maximise total exam-day recall under a
  daily time budget. That is the real optimal-control problem; this is a first,
  honest approximation of it.
- **Independent per card.** No interaction between cards, no topic weighting, no
  time budget. Ordering is purely by projected recall.
- **Whole-day rounding.** `days_to_exam` rounds toward zero; an exam today or in
  the past yields a 0-day cap (review now; schedule nothing beyond the deadline).

## Files

New, fork-only files (no upstream merge surface):

| File | Purpose |
| --- | --- |
| `rslib/src/scheduler/cfa_deadline.rs` | All engine logic: `Collection::deadline_retention` + pure helpers (`days_until`, `capped_interval`, `predicted_recall_at_exam`) + unit tests. |
| `pylib/anki/cfa_deadline.py` | Thin Python wrapper (RPC-preferred, read-only SQL parity fallback) + `DeadlineRetention` result dataclass. |
| `pylib/tests/test_cfa_deadline.py` | End-to-end Python tests. |
| `docs/cfa/DOK4-DEADLINE.md` | This note. |

Minimal additive edits to existing files:

| File | Change |
| --- | --- |
| `proto/anki/scheduler.proto` | +1 rpc `DeadlineRetention` at the end of `SchedulerService`; +2 messages (`DeadlineRetentionRequest`, `DeadlineRetentionResponse`) at the end. Existing `BuildExamQueue` lines untouched. |
| `rslib/src/scheduler/mod.rs` | +1 line: `mod cfa_deadline;`. |
| `rslib/src/scheduler/service/mod.rs` | +1 thin trait delegate `deadline_retention` (mirrors the existing `build_exam_queue` delegate). Required because the generated `SchedulerService` trait has no default methods; all real logic lives in `cfa_deadline.rs`. |
| `qt/aqt/cfa.py` | +1 "Peak-on-Exam-Day…" menu action + `PeakOnExamDayDialog`. |

Everything else (`_backend_generated.py`, the Rust service trait/dispatch,
`scheduler_pb2.py`) is **generated** from the proto — no hand edits.

## Invocation

```python
from anki import cfa_deadline

res = cfa_deadline.deadline_retention(
    col, deck_id=deck_id, exam_date="2026-08-25", fetch_limit=50
)
for cid, r, ivl in zip(res.card_ids, res.predicted_recall, res.suggested_interval_days):
    ...  # weakest-on-exam-day first; ivl is the deadline-capped suggestion
```

Or via the desktop UI: **CFA → Peak-on-Exam-Day…** (uses the deck's configured
exam date from `anki.cfa.set_exam_config`).

### Build note (RPC binding)

The Rust RPC and its Rust unit tests build and run from the `.proto` via the
cargo build scripts (`cargo test -p anki --lib`). The **Python** binding for the
new RPC (`scheduler_pb2.DeadlineRetentionRequest` + `_backend.deadline_retention`
+ the recompiled `_rsbridge`) is only regenerated by a full `just build`. Until
then, `cfa_deadline.deadline_retention` transparently uses the **read-only SQL
parity fallback**, which computes the same predicted recall via the engine's
`extract_fsrs_retrievability` function evaluated at the exam instant. Both the
Python test and the Qt dialog therefore work today; after a full build they use
the RPC unchanged (`DeadlineRetention.used_rpc` reports which path served).
