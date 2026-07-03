# BRAINLIFT — spiky POVs → shipped features → evidence (ankiCFA)

This maps the **three spiky POVs** from the project's `Brainlift.md` (worktree
root) to what actually shipped and the concrete, runnable evidence for each. The
POV text below is quoted **verbatim**. Standing caveats are at the bottom; the
live-app evidence is collected in the contact sheet at `demo/contact-sheet.png`
(source `demo/contact-sheet.html`).

Headline test reality (reproducible, not accounting):
`just cfa-f9-test-tally` → **203 passed, 1 skipped** (one deduplicated
collection); Rust **21** = `cargo test -p anki --lib -- scheduler::cfa_deadline`
(10) + `cargo test -p anki --lib -- scheduler::service::tests::exam_queue
scheduler::service::tests::verification_probe` (11). See `f9-tally-after.log`.

---

## POV 1 — Ethics as recall, and the boundary is the tested skill

> **Spiky POV 1**
> Ethics questions trouble CFA Level II candidates, and the solution usually
> cited is more recognition-based questions. However, the better way to
> internalize ethics is to treat CFA Level II vignette questions as recall
> questions. The learner should internalize a schema by being forced to answer
> with precision and state where the line sits.
>
> **Feature**
> Single scenarios teach labels. Near-miss pairs teach the boundary, and that
> boundary is the actual tested skill.

**Shipped →** **F1** (one-passage, multi-span ethics recall — 30 authored
passages / 73 gold evidence spans, clustered on confusable Standards such as
Suitability vs. MNPI vs. Diligence) and **F2** (semantic AI grading of the
highlighted evidence spans, with a deterministic F1 grader as the AI-off
fallback). The learner must both call the verdict **and** highlight the exact
words that put the conduct on one side of the line — recall of the boundary, not
recognition of a label.

**Evidence**
- Bank: `cfa/ethics_pairs/passages.jsonl` — 30 one-passage items (`wc -l` = 30).
- With-key grader eval: `proof/fixes/p4/f2-withkey-eval.txt` — the real LLM
  grades all 30 attempts at **0.933** agreement (≥ 0.80 → PASS); deterministic
  AI-off baseline 0.733 for contrast (`f2-withkey-eval.json`).
- Live on device: `demo/contact-sheet.png` mobile panels — the passage front
  (`54-ethics-passages`), the graded verdict + evidence-span scoring
  (`57-graded`), and a second "Ethical" case with highlighted spans
  (`60-ethical-highlighted`).
- Run it: `just cfa-passages-test` (F1 grader/schema/Py↔JS parity),
  `just cfa-ai-grade-test` (F2 grader + desktop bridge).

---

## POV 2 — Optimize retention for a single date, not forever

> The Anki algorithm is unoptimized for test prep for two reasons.
> FSRS optimizes for least cost for indefinite retention, while CFA requires
> optimal retention on a single date. These are two different optimization
> problems. The assumption of unlimited retention has been assumed at every
> stage, but retention must be optimized for the specific date of the test.
>
> **Feature**
> Date-aware scheduling: default SRS optimizes memory forever, but the learner
> enters the exam date and the engine back-plans every interval so recall peaks
> on test day.
> The algorithm should treat the exam as the endpoint. Cards that are weak,
> high-yield, or fast-decaying should be pulled forward. Cards that are already
> stable should be spaced out unless they need a final pre-exam refresh. The goal
> is not minimum review cost forever. The goal is maximum readiness on the test
> date.

**Shipped →** **F0b** (desktop exam-date picker "Peak-on-Exam-Day" that persists
the exam config + a "Study by Exam Priority" queue), the shared-engine Rust
scheduler `scheduler::cfa_deadline` (caps each card's suggested interval at
`min(FSRS interval, days-to-exam)` and orders by predicted recall so weak cards
surface first), the `BuildExamQueue` service that assembles the priority queue,
and **F4** (an exam-readiness call that scores against the exam date rather than
indefinite retention).

**Evidence**
- Rust date-aware core: `rslib/src/scheduler/cfa_deadline.rs` — e.g.
  `capped_interval_is_min_of_fsrs_interval_and_days_to_exam`,
  `suggested_interval_is_capped_at_days_to_exam`,
  `lower_predicted_recall_sorts_first` (10 tests, all green).
- Queue build + urgency: `rslib/src/scheduler/service/mod.rs` — e.g.
  `exam_queue_urgency_is_monotonic_in_days_to_exam`,
  `exam_queue_weaker_card_ranks_first_for_equal_weight` (part of the 11).
- Desktop UI: `demo/contact-sheet.png` panels — the CFA menu's "Peak-on-Exam-Day
  (Deadline)" action (`03-cfa-menu-crop`), the invoked "Study by Exam Priority"
  queue (`06-priority-crop`), and the readiness call (`04-exam-readiness-crop`).
- Run it: `just cfa-f0b-test`, `just cfa-f4-test`, and the two scoped
  `cargo test` commands above.

---

## POV 3 — Content-type-aware weighting (not one language-trained curve)

> FSRS was largely built from language-learning behavior data, while CFA content
> has different item types:
> formulas;
> ethics rules;
> conceptual distinctions;
> multi-step calculations;
> case-style application.
>
> **Feature**
> Content-type-aware weighting: one language-trained curve decays every card
> alike, but the engine tags each card by item type and tunes its spacing to how
> that type actually fades.
> Formula cards, ethics rules, conceptual distinctions, multi-step calculations,
> and case-style applications should not be scheduled the same way. High-yield,
> fast-decaying cards should resurface before they slip.

**Shipped →** every authored card carries exactly one closed-vocabulary
`type::<kind>` tag (formula / ethics-rule / conceptual / calculation /
case-application), and `BuildExamQueue` multiplies each card's urgency by a
per-type weight so equally-weak cards of different item types are scheduled
differently.

**Evidence**
- Classifier: `tools/cfa/build_cfa_deck.py` — `classify_item_type()` returns the
  `type::<kind>` tag, applied as `note.tags = [item["los_tag"],
  f"type::{classify_item_type(item)}"]`.
- Weighting in the engine: `rslib/src/scheduler/service/mod.rs` —
  `type_multiplier_for_tags(tags, &input.type_multipliers)`, proven by
  `exam_queue_type_multiplier_differentiates_equal_weakness_cards` (two equally
  weak cards, `type::formula` @ 0.85 vs `type::ethics-rule` @ 1.30, rank
  differently) and `exam_queue_untyped_card_defaults_to_unit_multiplier`.
- Python round-trip: `pylib/tests/test_cfa.py`.
- Run it: `just cfa-types-test` (classifier + the pylib multiplier round-trip).

---

## Honest caveats (these hold for the whole submission)

- **AI is OFF by default and every feature works fully without a key.** F2
  semantic grading falls back to the deterministic F1 grader, F3 tab-fill is
  disabled, and the eval's LLM ≥0.80 assertion is *skipped* (never faked). The
  with-key numbers (F2 0.933; F3 real drafted back) are the opt-in path, proven
  in `proof/fixes/p4/f2-withkey-eval.txt` and `proof/fixes/p4/f3-withkey-after.png`.
- **F4 readiness is not validated against real exam outcomes.** It is a Bayesian
  call over spaced-repetition recall (SM-2 fallback) against a ~65% MPS proxy,
  and carries a standing "not validated against real exam data" label in-product.
- **Mobile is the shared fork Rust engine + synced content, not a full port.**
  On Android the fork `BuildExamQueue` / `DeadlineRetention` engine runs
  on-device and the decks/ethics/exam-config reach the phone via bundled `.apkg`
  + AnkiWeb sync; the AI editor button, LLM grading UI, and readiness dialog are
  desktop-only (see `docs/cfa/PLATFORM-MATRIX.md`).
- **All authored items are original.** No copyrighted CFA Institute content; the
  leakage check confirms no held-out eval question overlaps a training front.

**See also:** the live-app contact sheet `demo/contact-sheet.png`
(`demo/contact-sheet.html`), the with-key proofs `proof/fixes/p4/f2-withkey-eval.{txt,json}`
and `proof/fixes/p4/f3-withkey-after.png`, and the reproducible tally in
`proof/fixes/p4/f9-tally-after.log`.
