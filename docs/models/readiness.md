# ReadinessModel

**Question answered:** "On the exam's own scale, how ready is the learner?"
A fabricated readiness number is an automatic fail, so this model either reports a
range **with** a confidence, or it abstains.

## Method
Builds on the PerformanceModel point + range, then maps to a **configurable**
scale (`ExamConfig`, exam-agnostic):

- `scale_type = "pass_fail"`: `point = P(pass)`. The performance band is treated as
  ±1σ around the point; `P(pass)` is the normal CDF mass above `pass_threshold`.
  The range comes from applying the same CDF at the band edges.
- `scale_type = "scaled"`: `point` and `range` are the performance point/band
  linearly mapped into `[scale_min, scale_max]`.

## Output (`Score`)
`{point, range, coverage_pct, confidence, updated_at, reasons, abstain}`.
- `confidence` combines coverage with the performance band width (wider band ⇒
  lower confidence).
- `range` is always present when not abstaining and always brackets `point`.

## Give-up rule
Abstain when `graded_reviews < 200` OR `coverage < 50%` (configurable in
`ExamConfig`). When abstaining, `point = range = None`, `confidence = 0`, and
`reasons` explain the insufficiency. This is the primary defence against emitting a
made-up readiness score.
