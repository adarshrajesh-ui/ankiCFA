# Model: Memory Score

_Score-mapping + model-description doc (Phase A / A11). Source of truth:_
`pylib/anki/cfa._py_memory_score` _(Python reference) and the Rust_
`compute_cfa_scores` _RPC in_ `rslib/src/scheduler/cfa_scores.rs` _(kept at
parity, verified by_ `just cfa-parity-test` _). No AI is involved — this is pure
spaced-repetition statistics._

## What it answers

> "Of the CFA syllabus I have studied, how well do I currently **retain** it?"

## Method

1. **Per-card retrievability.** For every card in scope we read the FSRS
   retrievability `R` — the model's probability that you would recall the card
   right now (`estimate_recall`). Cards with no memory state yet contribute no
   `R`.
2. **Group by topic.** Each card is mapped to exactly one canonical topic by a
   longest-prefix match of its `los::<topic>` tags (`_topic_of`) against the 10
   `CANONICAL_TOPICS`. Cards outside every configured topic are ignored.
3. **Per-topic range.** A topic's score is the **mean of its cards' `R` ± one
   population standard deviation**, clamped to `[0, 1]` (`_range`). The spread is
   the honest signal of "how evenly do I know this topic".
4. **Overall = exam-weight-weighted range.** The overall memory score is the
   topic means combined by each topic's **exam weight**, `± the weighted
   standard deviation` (`_weighted_range`). Weighting means a high-weight topic
   you know well cannot be masked by a low-weight topic you know poorly, and
   vice versa. If no exam weights are configured it falls back to an equal-weight
   mean.

## Range (never a bare number)

The score is always reported as `point ∈ [range_low, range_high]`, e.g.
`0.87 ∈ [0.79, 0.95]`. The band is the (weighted) standard deviation of per-topic
retrievability — it widens honestly when your knowledge is uneven across topics
and narrows as it becomes uniform. We never surface a single overconfident
number. `range_low`/`range_high`/`point` are `None` while abstaining.

Alongside the number the score reports **coverage** (`topics_covered /
topics_total`, on the fixed 10-topic denominator) and a full per-topic
breakdown, so a high overall score built on thin coverage is visible rather than
hidden.

## Give-up rule (enforced)

The app shows **"not enough data"** instead of a number until **all** of these
hold (`_giveup_reason`):

- **≥ `MIN_GRADED_REVIEWS` = 200** graded reviews in scope, **and**
- **≥ `MIN_TOPIC_COVERAGE` = 50 %** of canonical topics covered, **and**
- **no high-weight topic skipped** — if any topic whose exam weight is at or
  above the average configured weight has zero graded reviews, the score is
  invalidated regardless of the totals (a deck that skips a heavy topic cannot
  produce a trustworthy overall number).

Below any threshold the reason string states exactly which bar was missed and by
how much. Abstaining is a first-class, tested outcome — not an error.

## Honesty notes

- **Offline / AI-off identical.** The score is pure local Rust/Python; disabling
  AI or going offline changes nothing about this path (proven in
  `L1/crash-robustness.txt`).
- **Rust == Python parity** is enforced by test, so the desktop RPC and the
  Python reference return the same numbers.
- Calibration of this score (Brier / log loss / reliability) is measured
  separately in `cfa/eval/calibration.py` — see `L1/calibration.txt`.
