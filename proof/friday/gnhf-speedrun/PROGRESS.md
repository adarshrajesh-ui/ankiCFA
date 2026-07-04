# Speedrun PROGRESS (single GNHF run) — update after each item

Master plan: `proof/friday/SPEEDRUN-PLAN.md`. Mobile:
`/Users/adarshrajesh/wed/AnkiDroid/SPEEDRUN-MOBILE-PLAN.md`.
Legend: TODO / WIP / DONE (evidence path) / BLOCKED (root cause).

## Phase A — features
| Item | Status | Evidence |
|------|--------|----------|
| A1 AI-beats-baseline | DONE | `cfa/eval/baseline_compare.py` + 6 tests (`just cfa-eval-test`) + `just cfa-baseline-compare`; evidence `L1/baseline-compare.txt`. 3-way: deterministic-span 0.733, TF-IDF 0.933, LLM SKIPPED (AI OFF, honest). Gate `llm>max(baselines)` proven by oracle test (passes) + losing-AI test (fails) |
| A2 wrong-answer-rate gate | DONE | `cfa/ethics_pairs/eval_ai_grading.py` named gate `accuracy>=0.80 AND wrong_answer_rate<=0.20` (cutoffs `ACCURACY_CUT`/`WRONG_ANSWER_RATE_CUT`); +4 tests in `test_ai_grading.py` (23 pass); `just cfa-ethics-eval`; evidence `L1/eval-gate.txt`. AI-off war=0.000 (0/5 false-accepts), exits 0 honestly; SIMULATED oracle passes gate; false-accepting LLM (war 0.8) trips gate→exit 1 |
| A3 memory calibration (Brier/logloss/chart) | TODO | |
| A4 performance-model accuracy | TODO | |
| A5 paraphrase gap | TODO | |
| A6 card-gen gold set | TODO | |
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
