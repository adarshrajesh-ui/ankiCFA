# MemoryModel

**Question answered:** "How likely is the learner to recall a given card right now?"

## Method
FSRS-style retrievability on a power forgetting curve:

    R(t) = (1 + f · t/S) ^ d      d = -0.5,  f = 19/81

`t` is days elapsed since the last review; `S` (stability) is estimated per card
from its grade history (initial stability from the first grade, multiplicatively
grown on each successful recall, cut on a lapse). By construction `R = 0.9` when
`t == S`.

## Output (`Score`)
`{point, range, coverage_pct, confidence, updated_at, reasons, abstain}`.
- `point` = mean recall across modelled cards.
- `range` = mean of per-card intervals; each card's interval half-width shrinks
  as `1/sqrt(n_reviews+1)` (more reviews ⇒ tighter band).
- `confidence` scales with cards modelled and coverage.

## Calibration
Held-out protocol: for each card with ≥2 reviews, train on all reviews but the
last, predict recall for the last, compare to the observed outcome (grade ≥ 2 ⇒
recalled). We report a **reliability curve**, **Brier score**, and **log-loss**.
On the synthetic fixture Brier is well under 0.25.

## Give-up rule
Abstain when `graded_reviews < 200` OR `coverage < 50%` (thresholds configurable
in `ExamConfig`). An abstaining score carries `point = range = None` and lists the
reasons — never a fabricated recall number.
