# Model: Readiness Score

_Score-mapping + model-description doc (Phase A / A11). Source of truth:_
`pylib/anki/cfa._py_readiness_score` _(Python reference) and the Rust_
`compute_cfa_scores` _RPC in_ `rslib/src/scheduler/cfa_scores.rs` _(kept at
parity, verified by_ `just cfa-parity-test` _). No AI is involved._

> **Standing caveat (always shown):** `not validated against real exam data`
> (`READINESS_LABEL`). The readiness range is a real statistical confidence
> interval on your estimated exam accuracy, but it has never been checked
> against a real CFA result. Treat it as a direction, not a verdict.

## What it answers

> "Given what I have answered so far, what is a defensible range for my
> **exam accuracy** — and how sure are we about it?"

## Method

Readiness is a **Wilson 95% confidence interval on estimated exam accuracy**
(the 0–100% accuracy scale), and it is **always shown**.

1. **Point estimate** = the coverage-aware Bayesian exam-accuracy number
   (`bayes.accuracy`, from `_py_bayesian_readiness`). It starts at ~50% under
   the uniform prior and moves with graded first-exposure evidence, so a point
   always exists — no blend of separate scores, no hand-tuned margin.

2. **Interval** = a Wilson score interval sized by how many questions have been
   answered:

   ```
   n = first_exposures
   k = round(point · n)          # round-half-to-even, so Rust == Python
   (·, low, high) = wilson(k, n, 1.96)
   ```

   With **no questions answered** (`n == 0`) the interval is the whole range
   `[0.0, 1.0]` (0–100%); each additional distinct graded question narrows the
   band (width ~ 1/√n). The interval is clamped to always contain the point and
   to stay within `[0, 1]`.

The pass/fail _verdict_ itself is the separate **Bayesian** call, computed as
`P(exam accuracy ≥ MPS)` against a rough minimum-passing-standard proxy
`_MPS = 0.65`. **`_MPS = 0.65` is a heuristic, NOT the official CFA minimum
passing score** — the real MPS is not published. Readiness only supplies the
honest accuracy CI; the gated verdict lives with the Bayesian hero.

## Range (never a bare number)

Reported as `point ∈ [range_low, range_high]`, where `[range_low, range_high]`
is the Wilson 95% CI above. The band is widest (`0–100%`) with no evidence and
tightens as first exposures accrue. For transparency the score also carries the
`memory_point`, `performance_point`, and `coverage_pct` it was built from.

## Give-up rule

**None — readiness never abstains.** Unlike Memory and Performance (which
withhold a number below their evidence thresholds), readiness is _always_ shown:
with no data it honestly reports the entire `0–100%` range rather than "No
score", and the interval simply narrows as evidence accrues. `abstain` is always
`false` and `reason` is empty.

## Honesty notes

- **Offline / AI-off identical.** Pure local compute; disabling AI or going
  offline changes nothing (proven in `L1/crash-robustness.txt`).
- **A real CI, not a hand-tuned band.** The earlier ±0.15 margin and logistic
  `P(pass)` mapping are retired; the width now comes only from the Wilson
  interval, so it is grounded in the number of questions answered.
- **Uncalibrated pass verdict.** The `READINESS_LABEL` caveat travels with the
  score everywhere it is shown. The separate calibration harness
  (`cfa/eval/calibration.py`) measures Brier / log loss / reliability of the
  underlying recall probabilities.
- A separate **Bayesian readiness** number (`_py_bayesian_readiness`) supplies
  the F4 dashboard pass/fail call and its own 95% credible band; the readiness
  CI here reuses that Bayesian point as its centre.
- **Rust == Python parity** is test-enforced (`round_ties_even` matches Python's
  `round`, so both engines agree to 1e-9).
