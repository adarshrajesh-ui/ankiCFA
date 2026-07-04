# Speedrun PROGRESS (single GNHF run) — update after each item

Master plan: `proof/friday/SPEEDRUN-PLAN.md`. Mobile:
`/Users/adarshrajesh/wed/AnkiDroid/SPEEDRUN-MOBILE-PLAN.md`.
Legend: TODO / WIP / DONE (evidence path) / BLOCKED (root cause).

## Phase A — features
| Item | Status | Evidence |
|------|--------|----------|
| A1 AI-beats-baseline | DONE | `cfa/eval/baseline_compare.py` + 6 tests (`just cfa-eval-test`) + `just cfa-baseline-compare`; evidence `L1/baseline-compare.txt`. 3-way: deterministic-span 0.733, TF-IDF 0.933, LLM SKIPPED (AI OFF, honest). Gate `llm>max(baselines)` proven by oracle test (passes) + losing-AI test (fails) |
| A2 wrong-answer-rate gate | DONE | `cfa/ethics_pairs/eval_ai_grading.py` named gate `accuracy>=0.80 AND wrong_answer_rate<=0.20` (cutoffs `ACCURACY_CUT`/`WRONG_ANSWER_RATE_CUT`); +4 tests in `test_ai_grading.py` (23 pass); `just cfa-ethics-eval`; evidence `L1/eval-gate.txt`. AI-off war=0.000 (0/5 false-accepts), exits 0 honestly; SIMULATED oracle passes gate; false-accepting LLM (war 0.8) trips gate→exit 1 |
| A3 memory calibration (Brier/logloss/chart) | DONE | `cfa/eval/calibration.py` (Brier + log loss + 10-bin reliability + stdlib PNG encoder, no matplotlib); `run_eval.simulate()` refactor shares the DGP; +8 tests in `test_calibration.py` (20 pass via `just cfa-eval-test`); `just cfa-calibration`; evidence `L1/calibration.txt` + `L1/calibration.png`. SIMULATED cohort: Brier 0.2024, log loss 0.5909, ECE 0.0784 (< base-rate Brier); honest SIMULATED label + real-`--revlog` path that drops it |
| A4 performance-model accuracy | DONE | `cfa/eval/performance_eval.py` (stdlib logistic regression on topic mastery/difficulty/timing/coverage; whole-concept train/test split so neither paraphrase leaks); +8 tests in `test_performance_eval.py` (28 pass via `just cfa-eval-test`); `just cfa-performance-eval`; evidence `L1/performance-eval.txt`. SIMULATED cohort held-out accuracy 0.7217 (AUC 0.7161) vs majority baseline 0.6863 — beats baseline on every seed 0–5; stated gate `accuracy>=0.70 AND beats baseline` PASSes on seed 0, honest FAIL→exit 1 on seed 7 (0.6696) |
| A5 paraphrase gap | DONE | `cfa/eval/paraphrase_test.py` — rote recall on drilled card (`question_a`) vs reworded-question accuracy (`question_b`) over 30 held-out concepts; +10 tests in `test_paraphrase.py` (38 pass via `just cfa-eval-test`); `just cfa-paraphrase`; evidence `L1/paraphrase-gap.txt`. SIMULATED cohort: MEMORY recall 0.8492 vs PERFORMANCE 0.5908 → **gap 0.2583** (bootstrap 95% CI [0.2408, 0.2767], clears 0 → memory≠performance). Control `--rote-boost 0.0` collapses gap to −0.0317 (CI does not clear 0). Honest: give-up abstains below 30 learners/10 concepts; `--observations` scores real per-attempt data and drops the SIMULATED label (real non-distinguishable → exit 1); no AI involved so identical with AI off |
| A6 card-gen gold set | DONE | `cfa/eval/cardgen_gold.jsonl` (50 known-correct CFA QA, 5/topic, sampled from vetted `cfa/deck/*.jsonl`) + `cfa/eval/cardgen_check.py` (3-way classifier correct+useful / correct-but-bad / wrong, cutoff declared up front `correct_useful>=80% AND wrong<=10%`); +13 tests in `test_cardgen_check.py` (51 pass via `just cfa-eval-test`); `just cfa-cardgen-check`; evidence `L1/cardgen-check.txt`. SIMULATED default: 43 useful (86%) / 3 bad-card (6%) / 4 wrong (8%) → PASS; `--bad-sim` → 44% wrong → FAIL/BLOCKED. Real generator (`draft_back` via injected oracle) proven: good oracle PASSes gate; bad oracle FAILs → batch BLOCKED (exit 1). Honest: SIMULATED labelled, AI-off exits 0 (measurement), classifier is independent of the generator |
| A7 coverage map + topics 8→10 | TODO | |
| A8 ablation (3 builds) | TODO | |
| A9 50k benchmark | TODO | |
| A10 crash/offline robustness | TODO | |
| A11 score-mapping + model docs | TODO | |
| A12 unify Rust note | TODO | |
| A13 desktop installer (screenshots) | TODO | |
| A14 results report + Brainlift | TODO | |
| M1 mobile scores via RPC | TODO | |
| M2 desktop→phone reverse sync | TODO | |
| M3 same-card conflict merge | TODO | |
| M4 offline-then-sync + AI-off | TODO | |
| M5 packaged phone build | TODO | |

## Phase B — UI/UX passes (≥3, escalating; both apps)
| Pass | Desktop | Mobile | Log |
|------|---------|--------|-----|
| 1 (critical) | TODO | TODO | |
| 2 (harsher) | TODO | TODO | |
| 3 (ruthless) | TODO | TODO | |

Named must-fix: desktop Readiness renders with data; Connect/Logout redesigned;
native-CFA feel everywhere; AnkiDroid CFA UI full refactor.
