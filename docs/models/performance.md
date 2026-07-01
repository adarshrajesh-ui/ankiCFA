# PerformanceModel

**Question answered:** "How likely is the learner to answer a NEW, reworded exam
question correctly?" — deliberately distinct from raw flashcard recall.

## Method
For a question of `difficulty ∈ [0,1]` in a topic with mastery `m` (mean card
recall for that topic from the MemoryModel):

    P(correct) = m · paraphrase_transfer · (1 − 0.4 · difficulty)

`paraphrase_transfer < 1` (config, default 0.85) encodes that recognising a card
does not fully transfer to a paraphrased question.

## Paraphrase-gap metric
`paraphrase_gap = mean(card recall) − mean(reworded-question accuracy)` over shared
topics. Positive means questions are harder than flashcards. This metric is why
Memory and Performance can (and on the fixtures do) differ by a wide margin — a
key honesty guard against reporting "I memorised the deck" as "I'm exam-ready."

## Output (`Score`)
`{point, range, coverage_pct, confidence, updated_at, reasons, abstain}`.
- `point` = mean predicted P(correct) over questions.
- `range` widens with the empirical paraphrase gap, narrows with question count.
- `reasons` include the measured `paraphrase_gap`.

## Give-up rule
Abstain when `graded_reviews < 200` OR `coverage < 50%` (configurable in
`ExamConfig`). Abstaining scores carry `point = range = None` plus reasons.
