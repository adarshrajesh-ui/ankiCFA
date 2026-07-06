# Model: Performance Score

_Score-mapping + model-description doc (Phase A / A11). Source of truth:_
`pylib/anki/cfa._py_performance_score` _(Python reference) and the Rust_
`compute_cfa_scores` _RPC in_ `rslib/src/scheduler/cfa_scores.rs` _(kept at
parity, verified by_ `just cfa-parity-test` _). No AI is involved._

## What it answers

> "How likely am I to get a **fresh, unseen** exam question right?"

This is deliberately different from the memory score. Memory asks how well you
retain cards you have drilled; performance estimates transfer to a question you
have **not** recently studied — the thing the actual exam tests. (The gap
between the two is measured directly in `cfa/eval/paraphrase_test.py`; see
`L1/paraphrase-gap.txt`.)

## Method

1. **"New question" proxy = first exposure.** For every card in scope we take
   its **earliest graded review** (`min(revlog.id)` with `ease > 0`). That is
   the one time you answered the prompt with no recent study of it — the best
   available proxy for an unseen item.
2. **Correct = anything but _Again_.** On the Anki ease scale
   `1=Again, 2=Hard, 3=Good, 4=Easy`, a first exposure counts as **correct when
   `ease >= 2`** (`_CORRECT_EASE`); only _Again_ is a miss.
3. **Rate as a Wilson interval.** The performance score is the first-exposure
   success rate reported as a **95 % Wilson score interval** (`_wilson`, `z =
   1.96`), not a raw proportion. Wilson bounds stay inside `[0, 1]` and widen
   honestly on small samples — the correct shape for "how sure are we about this
   rate".

## Range (never a bare number)

Reported as `point ∈ [range_low, range_high]`, where `point` is the raw
first-exposure success rate and the bounds are the Wilson 95 % interval. The
interval is wide when few questions have been seen once and tightens as the
sample grows. `point`/`range_low`/`range_high` are `None` while abstaining. The
evidence fields `first_exposures` and `correct` are always populated.

## Give-up rule (enforced)

The app shows **"not enough data: N first-seen questions (need 30)"** instead of
a number until there are **≥ `MIN_FIRST_EXPOSURES` = 30** first exposures in
scope. Below that the sample is too thin to quote a rate, so the score abstains.
Abstaining is a first-class, tested outcome.

## Honesty notes

- **Offline / AI-off identical.** Pure local compute over the revlog; disabling
  AI or going offline changes nothing (proven in `L1/crash-robustness.txt`).
- **Held-out validation.** How well this notion of "fresh-question accuracy"
  actually predicts held-out exam-style questions is measured separately by the
  logistic-regression performance evaluator in `cfa/eval/performance_eval.py`
  (held-out accuracy vs a majority baseline; see `L1/performance-eval.txt`).
- **Rust == Python parity** is test-enforced.
