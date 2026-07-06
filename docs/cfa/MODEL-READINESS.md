# Model: Readiness Score

_Score-mapping + model-description doc (Phase A / A11). Source of truth:_
`pylib/anki/cfa._py_readiness_score` _(Python reference) and the Rust_
`compute_cfa_scores` _RPC in_ `rslib/src/scheduler/cfa_scores.rs` _(kept at
parity, verified by_ `just cfa-parity-test` _). No AI is involved._

> **Standing caveat (always shown):** `not validated against real exam data`
> (`READINESS_LABEL`). This is a coarse, deliberately-wide, **uncalibrated**
> P(pass) estimate. It has never been checked against a real CFA result. Treat
> it as a direction, not a verdict.

## What it answers

> "Roughly, what is my probability of **passing** if I sat the exam today?"

## Method

Readiness **fuses the memory and performance scores** with coverage, then maps
an estimated exam accuracy to a pass probability.

1. **Estimated exam accuracy** over the syllabus (`_acc`):

   ```
   acc = coverage · (0.5·memory + 0.5·performance) + (1 − coverage) · GUESS_RATE
   ```

   Covered syllabus contributes an equal blend of recall (memory) and
   fresh-question accuracy (performance); the **uncovered fraction is treated as
   guessing** on a 3-choice item (`_GUESS_RATE = 1/3`). Skipping syllabus
   therefore drags readiness down toward chance rather than being ignored.

2. **Accuracy → P(pass)** via a logistic map (`_pass_prob`):

   ```
   P(pass) = 1 / (1 + exp(−K·(acc − MPS)))
   ```

   with steepness `_READINESS_K = 8.0` and a rough pass threshold
   `_MPS = 0.65`. **`_MPS` is a heuristic, NOT the official CFA minimum passing
   score** — the real MPS is not published.

## Range (never a bare number)

Reported as `point ∈ [range_low, range_high]`. The point is `P(pass)` at the
blended accuracy; the bounds are computed by pushing the memory and performance
**range endpoints** through the same accuracy blend and logistic map, then
widening by an extra **`_READINESS_MARGIN = ±0.15`** to reflect model
uncertainty on top of the propagated statistical intervals. This makes the
readiness band intentionally the widest of the three scores. `point` and bounds
are `None` while abstaining. For transparency the score also carries the
`memory_point`, `performance_point`, and `coverage_pct` it was built from.

## Give-up rule (enforced)

Readiness **abstains whenever either input score abstains** — a readiness number
is only as trustworthy as the memory and performance scores beneath it. The
reason string names which input(s) abstained and why (propagated from
`MIN_GRADED_REVIEWS` / `MIN_TOPIC_COVERAGE` / skipped-high-weight-topic for
memory and `MIN_FIRST_EXPOSURES` for performance). Abstaining is a first-class,
tested outcome.

## Honesty notes

- **Offline / AI-off identical.** Pure local compute; disabling AI or going
  offline changes nothing (proven in `L1/crash-robustness.txt`).
- **Uncalibrated by design.** The `READINESS_LABEL` caveat travels with the
  score everywhere it is shown. The separate calibration harness
  (`cfa/eval/calibration.py`) measures Brier / log loss / reliability of the
  underlying recall probabilities — the readiness _pass-mapping itself_ is not
  claimed to be calibrated.
- A separate **Bayesian readiness** number (`_py_bayesian_readiness`) exists for
  the F4 dashboard that, unlike this score, never abstains and simply widens its
  band when evidence is thin; the two are complementary and both documented in
  code.
- **Rust == Python parity** is test-enforced.
