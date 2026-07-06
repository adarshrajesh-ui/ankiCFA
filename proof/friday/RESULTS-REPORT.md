# CFA Level II Exam-Prep — Consolidated Results Report

> **A14 deliverable.** Every measured / simulated number from the Phase A
> evaluation, benchmark, ablation, calibration and robustness work, assembled in
> one place — **including the results that did not clear their bar**. Each row
> links to the raw evidence file under `proof/friday/gnhf-speedrun/L1/` and the
> `just` recipe that reproduces it.
>
> **Honesty rule.** Anything marked `SIMULATED` is synthetic data used to
> validate the model math + metric code, not a real-world effect size. Anything
> marked `MEASURED` is the real built backend / real deck. The app scores with
> **AI switched OFF** everywhere; no number here required an OpenAI key.

Reproduce the whole report's evidence: run each recipe in the table, then
`just cfa-results-test` to confirm every cited evidence file exists and every
headline number in this document still matches its source.

---

## 1. Headline scorecard

| #   | Deliverable                          | Kind                    | Headline result                                                   | Bar                               | Verdict                                 | Evidence                       |
| --- | ------------------------------------ | ----------------------- | ----------------------------------------------------------------- | --------------------------------- | --------------------------------------- | ------------------------------ |
| A1  | AI beats a simpler baseline          | MEASURED (AI-off)       | TF-IDF 0.933 > deterministic-span 0.733; **LLM SKIPPED (AI off)** | LLM > max(baselines)              | **UNPROVEN — AI off** (honest null)     | `L1/baseline-compare.txt`      |
| A2  | Wrong-answer-rate gate               | MEASURED (AI-off)       | war **0.000** (0/5 false-accepts); accuracy 0.733                 | acc≥0.80 AND war≤0.20             | war leg PASS, acc leg **FAIL** (AI off) | `L1/eval-gate.txt`             |
| A3  | Memory calibration                   | SIMULATED               | Brier **0.2024**, log loss 0.5909, ECE 0.0784                     | < base-rate Brier (0.247)         | **PASS** (metric/math validated)        | `L1/calibration.txt` + `.png`  |
| A4  | Performance-model accuracy           | SIMULATED               | held-out acc **0.7217** (AUC 0.7161) vs baseline 0.6863           | acc≥0.70 AND beats baseline       | **PASS** (seed 0); see §4 caveat        | `L1/performance-eval.txt`      |
| A5  | Paraphrase memory-vs-performance gap | SIMULATED               | gap **0.2583** (95% CI [0.2408, 0.2767])                          | CI clears 0 AND gap≥0.02          | **PASS** (distinguishable)              | `L1/paraphrase-gap.txt`        |
| A6  | Card-gen gold-set checker            | SIMULATED               | 86% useful / 6% bad / 8% wrong                                    | useful≥80% AND wrong≤10%          | **PASS**; bad batch BLOCKED             | `L1/cardgen-check.txt`         |
| A7  | Coverage map + topics 8→10           | MEASURED (real deck)    | **10/10 topics covered**, 711 cards; Rust==Python==outline        | all 10 covered, 3-way parity      | **PASS**                                | `L1/coverage-map.txt` + `.png` |
| A8  | Study-feature ablation (3 builds)    | SIMULATED               | ON 0.6435 > OFF 0.6157 > PLAIN 0.5626                             | ON−PLAIN CI clears 0              | **PASS**; honest null holds (§4)        | `L1/ablation.txt`              |
| A9  | 50k-card benchmark                   | MEASURED (real backend) | next-card p50 **0.036 ms**; dashboard **220 ms**                  | < 1s interaction budget           | **PASS**; dashboard = bottleneck (§4)   | `L1/bench.txt`                 |
| A10 | Crash + offline robustness           | MEASURED (real backend) | **20/20 SIGKILLs → CLEAN**; revlog 280→4358                       | 0 corruption; AI-off still scores | **PASS**                                | `L1/crash-robustness.txt`      |
| A11 | Score-mapping + model docs           | DOCS + test             | 3 MODEL-*.md; 5-test doc-drift guard                              | docs match code constants         | **PASS**                                | `L1/model-docs.txt`            |
| A12 | Unified Rust-change note             | DOCS + test             | all 3 RPCs; **24 Rust tests**                                     | note matches build                | **PASS**                                | `L1/rust-engine-note.txt`      |
| A13 | Desktop installer (screenshots)      | MEASURED (real DMG)     | 226 MB macOS DMG; 3-shot clean-machine install                    | self-contained + boots CFA Home   | **PASS** (macOS); win/linux not built   | `L1/installer/`                |

---

## 2. What worked

- **The engine scores with AI hard-off, offline, everywhere.** A10 proves
  `compute_cfa_scores` returns real memory / performance / readiness ranges with
  `cfa_ai_enabled=False` and no network — because scoring is pure local
  Rust/Python, no LLM path is even touched.
- **The three scores are genuinely distinct measurements.** A5's paraphrase gap
  (0.2583, CI clears 0) shows memory-on-the-drilled-card and
  performance-on-the-reworded-question are statistically distinguishable — the
  product's core claim ("Memory ≠ Performance ≠ Readiness") is not just a label.
- **The exam-priority queue produces a real, weight-driven lift.** A8's ON−PLAIN
  effect (+0.0809, CI clears 0) holds on every seed 0–5, and the uniform-weights
  null control collapses ON−OFF to exactly 0.0 — proving the edge comes from
  exam-weighting, not a modeling artifact.
- **Coverage is complete and consistent across languages.** A7 covers all 10
  official CFA Level II areas from the real deck (711 cards) with Rust == Python
  == outline three-way parity.
- **The build is crash-safe and fast.** A10: 20/20 force-kills mid-review left
  zero corruption. A9: next-card and answerCard are sub-millisecond at p50/p95
  even on a 50k-card deck.
- **The gates and docs can't silently rot.** A2/A6 declare cutoffs up front and
  BLOCK failing batches; A11/A12 ship stdlib doc-drift guards that go red if a
  documented constant or test count drifts from the code.

## 3. Results that did NOT clear their bar (honest)

These are reported deliberately — a report that only lists wins is dishonest.

- **A1 — "AI beats the baseline" is UNPROVEN in this run.** With no
  `OPENAI_API_KEY`, the LLM leg is SKIPPED, so we cannot demonstrate the AI beats
  the baseline. Worse for the AI's case: the _simpler_ TF-IDF keyword baseline
  (0.933) already beats the deterministic-span grader that actually ships when AI
  is off (0.733). The harness _proves it would catch a losing AI_ (a mocked LLM
  scoring below the baseline trips the gate → exit 1), but the positive claim
  itself waits on a real key. Not fabricated to look good.
- **A2 — the AI-off accuracy leg FAILS its own gate.** The deterministic fallback
  grades at 0.733, below the ACCURACY_CUT of 0.80, so the named gate honestly
  shows FAIL for the AI-off leg. The process still exits 0 (AI-off contract): the
  gate is an _AI acceptance bar_, not an AI-off pass/fail. The wrong-answer-rate
  leg does pass (0.000).
- **A4 — held-out accuracy dips below the 0.70 cut on unlucky seeds.** Seed 0 =
  0.7217 (PASS) but seed 7 = 0.6696 (FAIL → exit 1, tested explicitly). With only
  10 held-out concepts there is real small-sample variance; the _robust_ invariant
  is "beats the majority baseline on every seed," which holds, while the fixed
  0.70 cut is asserted only on the default seed.
- **A8 — the honest null is a documented "null," not a win.** Under
  `--uniform-weights` the ON−OFF effect is exactly 0.0 (CI includes 0). This is
  the intended negative control, reported as NULL rather than hidden.
- **A5 — the zero-boost control is a deliberate non-result.** With
  `--rote-boost 0.0` the gap collapses to −0.0317 (CI fails to clear 0):
  "NOT DISTINGUISHABLE." Reported to prove the measured gap is driven by the
  modeled rote advantage, not a wording artifact.
- **A9 — the dashboard is the bottleneck.** `compute_cfa_scores` recomputes over
  the whole 50k collection every call (~220 ms cold AND warm — no cache). Still
  under a 1s once-per-open budget, but it is the honest thing to optimize next.
- **A13 — Windows / Linux installers were NOT built this run.** Only the macOS
  DMG was produced (the host platform). The cross-platform Briefcase path exists
  and is unchanged; the other two need their toolchains/submodules.
- **Almost everything statistical here is SIMULATED.** A3/A4/A5/A6/A8 run on
  synthetic cohorts. They validate the model math and the metric code; they are
  **not** real-world effect sizes. Each carries the `SIMULATED` label and a
  `--revlog` / `--observations` path to drop it once real data exists.

## 4. Standing caveats

- **Readiness is not validated against real exam pass/fail data.** The readiness
  model carries the standing caveat `not validated against real exam data`
  (documented in `docs/cfa/MODEL-READINESS.md`); it reports a wide uncalibrated
  band and abstains when either input abstains.
- **The give-up rule is enforced, not decorative.** Every eval abstains below its
  data threshold (e.g. A5 <30 learners/<10 concepts; A8 <30 learners; memory
  <200 graded reviews; performance <30 first exposures).
- **Numbers are host-specific.** A9/A10 timings were measured on Darwin arm64,
  py3.13.13; percentiles will differ on other hardware.

---

## 5. Full number appendix (per deliverable)

### A3 — Memory calibration (SIMULATED, 12,000 reviews)

Base rate (recall) 0.5563; mean prediction 0.6347. **Brier 0.2024 · log loss
0.5909 · ECE (10-bin) 0.0784.** 10-bin reliability table + chart in
`L1/calibration.png`. Beats the base-rate Brier (0.5563·(1−0.5563) = 0.247).

### A4 — Performance-model accuracy (SIMULATED, 120 learners)

4 features (topic mastery, difficulty, timing, coverage); whole-concept
train/test split (no paraphrase leakage), 10 of 30 concepts held out, 2,400 test
rows. **Held-out accuracy 0.7217, AUC 0.7161, majority baseline 0.6863.** Beats
baseline on every seed 0–5 (0.7033–0.7362 vs 0.6717–0.7083).

### A5 — Paraphrase gap (SIMULATED, 200 learners, 30 concepts × 2)

Rote boost 0.30 mastery units. **Memory recall 0.8492 vs Performance 0.5908 →
gap 0.2583** (bootstrap 95% CI [0.2408, 0.2767]; per-concept min/mean/max
0.1050/0.2583/0.4000). Control `--rote-boost 0.0` → gap −0.0317 (CI
[−0.0453, −0.0182], not distinguishable).

### A6 — Card-gen gold set (50 CFA QA, 5/topic × 10 topics)

Declared cutoff `correct_useful ≥ 80% AND wrong ≤ 10%`. SIMULATED default: 43
useful (86%) / 3 bad (6%) / 4 wrong (8%) → PASS. `--bad-sim`: 25/5/20
(50%/10%/40%) → FAIL, batch BLOCKED.

### A8 — Study-feature ablation (SIMULATED, 200 learners × 10 topics)

Same cohort / same 60-question held-out exam / equal 42-of-120-card budget across
all 3 arms. Exam-weighted accuracy: **ON 0.6435 [0.6353, 0.6523] · OFF 0.6157 ·
PLAIN 0.5626.** Effects: **ON−OFF +0.0279 [+0.0220, +0.0337]** · **ON−PLAIN
+0.0809 [+0.0736, +0.0883]** (both clear 0). Uniform-weights null: ON−OFF exactly
0.0, ON−PLAIN survives (+0.0457).

### A9 — 50k-card benchmark (MEASURED, real backend, offline, no AI)

50,000 cards, 17,500 studied. p50 / p95 / worst (ms): next-card 0.036 / 0.044 /
32.5 · answerCard ack 0.077 / 0.110 / 6.9 · dashboard cold 220.4 · dashboard warm
219.1 / 222.3 / 239.0 · sync (real anki-sync-server round-trip) 8.8 / 13.4 / 13.4.

### A10 — Crash + offline robustness (MEASURED)

20/20 SIGKILLs mid-review → every reopen CLEAN (backend integrity check); revlog
grew 280 → 4358. Offline + AI-off: memory 0.9985 [0.9942, 1.0000] · performance
0.7500 [0.5981, 0.8581] · readiness [0.6130, 1.0000].

### A1 / A2 — AI grading vs baselines (MEASURED, AI-off; 30 ethics attempts)

Grade agreement with the human 4-way label: deterministic-span 0.733, TF-IDF
0.933, LLM `---` (AI off). Wrong-answer-rate 0.000 (0/5 human-incorrect
false-accepted). A mocked oracle LLM (labeled SIMULATED, no real API call) hits
1.000 agreement and passes both gate legs, demonstrating the gate mechanism.

### A7 — Coverage map (MEASURED, real deck)

All 10 CFA Level II areas covered; 711 authored cards; per-topic deck share
5.3%–13.4%. Rust `CANONICAL_TOPICS` == Python == `level2_topics.json` outline.

### A11 / A12 / A13 — Docs + installer

A11: 3 MODEL-*.md (method + range + give-up rule each), 5-test doc-drift guard.
A12: `RUST_ENGINE_NOTE.md` covers 3 RPCs; 24 Rust tests (11 exam-queue + 10
deadline + 3 scores); 6-test drift guard. A13: real 226 MB macOS DMG, verifier
confirms self-contained + all 8 CFA modules, 3-shot clean-machine install.
