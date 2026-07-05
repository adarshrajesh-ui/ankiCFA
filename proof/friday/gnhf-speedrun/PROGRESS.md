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
| A7 coverage map + topics 8→10 | DONE | `cfa/outline/level2_topics.json` (10 official CFA L2 areas + exam-weight bands); `CANONICAL_TOPICS` extended 8→10 in **both** `pylib/anki/cfa.py` and `rslib/src/scheduler/cfa_scores.rs` (added `los::derivatives` + `los::fixed-income` — the hyphenated prefix the deck's Fixed Income cards actually carry, so both match), keeping Rust==Python==outline three-way parity (proven in `L1/coverage-map-verify.txt`). Coverage map renderer `cfa/outline/coverage_map.py` (stdlib PNG + 5×7 bitmap font, REAL deck-derived data) + 11 tests (`just cfa-outline-test`) + `just cfa-coverage-map`; evidence `L1/coverage-map.png` + `L1/coverage-map.txt` (all **10/10 topics covered**, 711 cards). Updated `topics_total==8`→canonical in `test_cfa.py`/`test_cfa_f4.py`/`test_cfa_f4_dialog.py` + the Rust `happy_path`/empty-collection tests (band width is N-dependent: ~0.358 at 10 vs ~0.400 at 8). Verified: `cargo test scheduler::cfa_scores` 3✓, `cfa-scores-test` 10✓, `cfa-parity-test` 2✓, `cfa-f4-test` 19+6✓, `cfa-deck-test` 15✓ |
| A8 ablation (3 builds) | DONE | `tools/cfa/ablation_harness.py` + `just cfa-ablation` — the exam-priority points-at-stake queue ablated across **3 builds** (ON=weight×weakness / OFF=weakness-only / PLAIN=deck order) on the SAME cohort, held-out exam, and equal study-time budget (42/120 cards). Pre-registered metric **exam-weighted accuracy** reported WITH A RANGE (bootstrap 95% CI). SIMULATED default: ON 0.6435 [0.6353,0.6523] > OFF 0.6157 > PLAIN 0.5626; **ON−OFF +0.0279 [+0.0220,+0.0337]** and **ON−PLAIN +0.0809 [+0.0736,+0.0883]**, both CIs clear 0. Honest null (`--uniform-weights`): ON key collapses onto OFF → ON−OFF **exactly 0.0** while ON−PLAIN survives (+0.0457) — proves the ON edge is driven by exam-weighting. ON−PLAIN clears 0 on every seed 0–5. +12 tests (`just cfa-ablation-test`); give-up abstains <30 learners (exit 0); `--observations FILE` scores real per-learner arm outcomes and gates on the hypothesis (good→exit 0, null→exit 1); SIMULATED labelled, no AI. Evidence `L1/ablation.txt` |
| A9 50k benchmark | DONE | `tools/cfa/bench.py` + `just bench` (`just bench-smoke` for CI) — builds a **50,000-card** CFA collection (10 canonical topics, 17,500 studied review cards w/ FSRS state + graded revlog) and times the hot ops against the **REAL built backend** (offline, no AI), printing **p50/p95/worst**: next-card 0.036/0.044/32.5 ms; answerCard ack 0.077/0.110/6.9 ms; dashboard first-load (cold `compute_cfa_scores`) 220 ms; dashboard refresh (warm) 219/222/239 ms; sync (REAL incremental `sync_collection` vs a local `anki-sync-server` subprocess, 8/8 normal rounds) 8.8/13.4/13.4 ms. Honest finding: the dashboard RPC recomputes over the whole 50k deck each call (~220 ms, no cache) — the real bottleneck, still under a 1s once-per-open budget. +9 tests (`just cfa-bench-test`, all 36 tools/cfa tests green); MEASUREMENT not SIMULATED. Evidence `L1/bench.txt` |
| A10 crash/offline robustness | DONE | `pylib/tests/test_cfa_crash_robustness.py` + `pylib/tests/cfa_crash_worker.py` + `just cfa-crash-test` (4 tests, green vs the REAL built backend). **Kill mid-review 20×→zero corruption:** a subprocess reviews cards in a tight loop (real revlog + card-state writes each iteration), the parent SIGKILLs it at random offsets AFTER the first review commits, then reopens and runs the backend integrity check (`fix_integrity`→`check_database`/`quick_check`) — all 20 reopens report **CLEAN** and revlog grows **280→4358** (reviews interrupted, survived, no corruption). **Offline + AI-off still scores:** with `cfa_ai_enabled=False` and no `OPENAI_API_KEY`, memory 0.9985 [0.9942,1.0000] / performance 0.7500 [0.5981,0.8581] / readiness [0.6130,1.0000] all return real ranges (pure local compute, no LLM path). Evidence `L1/crash-robustness.txt` |
| A11 score-mapping + model docs | DONE | `docs/cfa/MODEL-MEMORY.md` + `MODEL-PERFORMANCE.md` + `MODEL-READINESS.md` — one short page each with **method + range + give-up rule**, written straight from the `pylib/anki/cfa.py` reference (Rust `compute_cfa_scores` at parity). Memory = exam-weight-weighted per-topic FSRS-R mean ± weighted stdev, give-up = `MIN_GRADED_REVIEWS`=200 AND `MIN_TOPIC_COVERAGE`=50% AND no high-weight topic skipped. Performance = first-exposure success rate as a Wilson 95% interval, give-up = `MIN_FIRST_EXPOSURES`=30. Readiness = coverage-blended memory+performance → logistic P(pass) (`_MPS`=0.65, `_READINESS_K`=8.0, ±`_READINESS_MARGIN`=0.15, uncovered→`_GUESS_RATE`=1/3), abstains if either input abstains, carries the standing `not validated against real exam data` caveat. Doc-consistency test (`just cfa-model-docs-test`, 5 tests) asserts every documented constant matches the code so docs can't drift; full `cfa-eval-test` suite 56 green. Evidence `L1/model-docs.txt` |
| A12 unify Rust note | DONE | `docs/cfa/RUST_ENGINE_NOTE.md` rewritten to cover **all 3 read-only Rust RPCs** (`BuildExamQueue` / `DeadlineRetention` / `ComputeCfaScores`) — each with what-it-is, the 4 why-Rust reasons (shared engine→mobile, FSRS internals, 50k perf, core-testable), the exact upstream files touched (proto +3 rpcs/+6 msgs additive; `scheduler/mod.rs` +2 `mod` lines; `service/mod.rs` additive; new fork-only `cfa_deadline.rs`/`cfa_scores.rs`/`cfa.py`/`cfa_deadline.py`), and a **low** merge-difficulty verdict. **Fixed the stale test count** (was "8 unit tests" for one RPC → now the authoritative per-RPC breakdown: 11 exam-queue + 10 deadline + 3 scores = **24**). Verified against the real build: `cargo test -p anki --lib -- scheduler::cfa_scores scheduler::cfa_deadline exam_queue` → **24 passed**. New stdlib doc-drift guard `cfa/eval/tests/test_rust_engine_note.py` (6 tests, `just cfa-rust-note-test`) counts the `#[test]` attrs in the 3 Rust files and fails if the note's counts/RPC names/file citations drift; full `cfa-eval-test` suite now **62 green**. Evidence `L1/rust-engine-note.txt` |
| A13 desktop installer (screenshots) | DONE | **REAL** packaged installer `out/installer/dist/anki-26.05-mac-apple.dmg` (226 MB UDIF bzip2, sha256 `8845dfcf…6b0b`, ver 26.5) built via `tools/build-installer`. **Clean-machine install proof:** dragged `Anki.app` out of the DMG into an isolated dir (`/tmp/cfa-clean-install`) with a brand-new `ANKI_BASE` profile (no prior data), launched using ONLY the runtime it bundles (own `Python.framework` + `PyQt6`, 655M self-contained) → boots the native CFA **Exam Home** with honest empty-state scores. **Ordered screenshot sequence (NO VIDEO)** `L1/installer/`: `01-dmg-drag-install.png` (drag-to-Applications) → `02-clean-first-run-language.png` (fresh-profile language picker) → `03-clean-cfa-exam-home.png` (native CFA chrome + "Not enough data" cards on a fresh install). Verifier `tools/cfa/verify_installer.py` (`just cfa-installer-verify`) confirms self-contained + all 8 required CFA modules baked in (`RESULT: PASS`); +10 tests `just cfa-installer-test` (synthetic good/stock/partial/non-self-contained/versionless fixtures + real-bundle check). Evidence `L1/installer/installer.txt`. Windows/Linux packages NOT built this pass (need those toolchains/submodules); cross-platform `build_installer.py` path exists & unchanged. |
| A14 results report + Brainlift | DONE | `proof/friday/RESULTS-REPORT.md` — consolidated scorecard for **all A1–A13** (headline result / bar / verdict / evidence link each), a "what worked" section, an honest **"results that did NOT clear their bar"** section (A1 AI-beats-baseline UNPROVEN under AI-off — the simpler TF-IDF baseline 0.933 even beats the shipped deterministic-span 0.733; A2 AI-off accuracy 0.733<0.80 FAILs its own gate leg; A4 dips <0.70 on unlucky seeds; A8 uniform-weights null; A5 zero-boost control; A9 ~220ms dashboard bottleneck; A13 win/linux not built; nearly all stats SIMULATED), standing caveats, and a per-deliverable number appendix. `Brainlift.md` updated with a **"Product Validation"** DOK section tying each spiky POV to its measured/SIMULATED evidence and the core "Memory ≠ Performance ≠ Readiness" claim (gap 0.2583). Stdlib drift-guard `cfa/eval/tests/test_results_report.py` (5 tests, `just cfa-results-test`): every cited `L1/` evidence file exists, every headline number appears verbatim in BOTH the report and its source file, honesty scaffolding (SIMULATED / UNPROVEN / not-validated / bottleneck) present, A1–A13 rows all present; full `cfa-eval-test` suite now **67 green**. Evidence `L1/results-report.txt` |
| M1 mobile scores via RPC | DONE | Rebuilt the fork Android backend (AAR + host testing dylib) from `~/AlphaWeek2/ankiCFA` main so the shared Rust `compute_cfa_scores` RPC is compiled in and surfaced as `col.backend.computeCfaScores(deckId, wholeCollection, now)` (Kotlin binding GeneratedBackend.kt:1561; `.so` has 8 `compute_cfa_scores` symbols, host `.dylib` 2). `CfaScoresProvider.scores()` now prefers the RPC → `CfaScores(source=rpc)` and transparently falls back to the deterministic on-device `CfaScorer` (source=fallback) on absence/error, logging provenance. **Honest parity finding:** the RPC dedupes graded reviews per card-day (anti-cram) while the Kotlin fallback counted every revlog row (36 vs 216); fixed the fallback to match the engine's day-bucket formula so desktop==phone on the MIN_GRADED_REVIEWS give-up rule — after which RPC and fallback agree to **1e-6** on every score point+range. Also fixed `CfaExamQueue` for the engine's new `buildExamQueue(typeMultipliers)` arity. Verify: `just`-style `./gradlew :AnkiDroid:testPlayDebugUnitTest --tests "*.cfa.CfaScoresProviderTest/CfaScorerTest/CfaExamQueueTest"` → **3+2+1 green**, runtime log `source=rpc (shared Rust engine)`. Mobile branch `gnhf/speedrun-mobile`, evidence `AnkiDroid: proof/gnhf-speedrun/L3/scores-rpc.txt`. |
| M2 desktop→phone reverse sync | DONE | **Device-observable** on `emulator-5554`: two causal desktop reviews (unique revlog ids `1783211725074`, `1783211928235`) made on the desktop side against the local anki-sync-server, uploaded, then the phone synced + cold-relaunched. On-disk phone collection persists revlog **24→26→28**, both desktop cards reps **2→3**, and BOTH desktop-generated revlog ids present on the phone; the phone **Exam Readiness** screen increments **25→26 graded reviews** (one per desktop review) and honestly ABSTAINS ("N/A — abstaining", need 200) rather than fabricating scores. The HANDOFF "on-disk diverges/resets across cold launch" concern does **NOT reproduce** — it was a measurement artifact (reading the main `.anki2` while un-checkpointed synced reviews sat in the WAL); after a clean cold-stop the WAL checkpoints (round 1: main file 26, WAL 0 bytes) or applies on next open (round 2: 28). No engine fix needed; IntentHandler CFA-routing concern also stale (branch launches straight to DeckPicker). Corroborated engine-level by desktop `pytest pylib/tests/test_cfa_sync.py` → **7 passed** (forward/reverse/conflict). Mobile branch `gnhf/speedrun-mobile`, evidence `AnkiDroid: proof/gnhf-speedrun/L3/reverse-sync/` (3-shot screenshot sequence + `reverse-sync.txt` + reproducible `cfa_desktop_review.py`). |
| M3 same-card conflict merge | DONE | **Device-observable** on `emulator-5554`. Card X=`1783137755188` reviewed on BOTH devices diverged from a shared base: PHONE answered **Again** (ease 1) OFFLINE (airplane mode) → phone revlog `1783212583931`, card into learning; DESKTOP then answered **Easy** (ease 4) at a LATER time (revlog `1783212648010`) from the same base and uploaded. Phone came online + synced → converged phone collection (pulled from device, WAL applied): the **more-recent desktop review WON** — card X `queue=2 (review), ivl=4d, mod=1783212648` (phone's Again learning state overridden) — while the phone's own Again revlog row **is still present** (no lost review) and `reps=1` (no double-count). DeckPicker visibly `"2 0 0"→"1 1 0"` (phone Again → learning) `→"2 0 0"` (desktop Easy graduated it back to review). Documented rule = `resolve_review_conflict` "more-recent review wins" (state), append-only revlog (both rows persist). Honest: Readiness's displayed graded count is RAW (26→28); engine anti-cram DEDUPED count is 21 (same-card same-day → one (card,day)). Corroborated by desktop `pytest test_cfa_sync.py::test_conflict_more_recent_wins*` (**12/12**) + full file **20/20** after fixing a pre-existing same-ms collection-mod sync flake (50ms settle in `_review`). Mobile branch `gnhf/speedrun-mobile`, evidence `AnkiDroid: proof/gnhf-speedrun/L3/conflict-merge.txt` + `conflict-merge/` (5-shot sequence + `cfa_desktop_conflict_review.py`). |
| M4 offline-then-sync + AI-off | DONE | **Device-observable** on `emulator-5554`. Base phone=server=31 revlog. Airplane mode ON (device `ping 10.0.2.2` "Network is unreachable", status-bar airplane icon) → answered card `1783137755189` **GOOD offline** → phone revlog **31→32**, offline revlog id `1783213842513`; server still 31 and the id is **absent** (`found_on_server:false`) = genuine offline-only. STILL OFFLINE, opened **Exam Readiness** → it **RENDERS** (`Source: on-device (deterministic)`, no AI/no network): honest `N/A — abstaining` with full give-up reasons, footer **28→29 graded reviews** / 20→21 first exposures reflecting the offline review — **proves AI-off still scores** (mobile score path is 100% local RPC/fallback; airplane kills sync server AND the AI proxy). Airplane OFF → the Sync icon shows an **orange pending-upload dot** → tapped Sync → device logcat `anki::sync::collection::chunks: sending done=true cards=1 notes=0 revlog=1` + `finalize` + media sync complete; icon went clean. **Ground truth:** server on-disk collection (`/tmp/cfa-syncserver/cfa/collection.anki2`) revlog **31→32** and the phone's exact offline id `1783213842513` (cid `1783137755189`, ease=3 Good) now **present** (`found_on_server:true`, re-verified by a fresh full-download). The phone couldn't invent that ms id → airtight causal upload proof. Engine-level corroboration: desktop `pylib/tests/test_cfa_sync.py` round-trip (green, M2/M3). Mobile branch `gnhf/speedrun-mobile`, evidence `AnkiDroid: proof/gnhf-speedrun/L3/offline-then-sync.txt` + `offline-then-sync/` (6-shot sequence + `cfa_server_inspect.py`). |
| M5 packaged phone build | DONE | **SIGNED release APKs** built on `gnhf/speedrun-mobile`: `./gradlew :AnkiDroid:assembleFullRelease` (full flavor, R8/minify ON, per-ABI splits) → 4 APKs (`AnkiDroid-full-{arm64-v8a,armeabi-v7a,x86_64,x86}-release.apk`, arm64 65 MB sha256 `c22ee390…`), versionName 2.25.0alpha1, applicationId `com.ichi2.anki`. Signed with the repo fallback release keystore (`tools/fallback-release-keystore.jks`): `apksigner verify -v` → **Verifies / v2 scheme: true**, signer SHA-256 `0a8ebeea…` EXACTLY matching the keystore `my-key` entry. Packaged `librsdroid.so` is the CFA fork engine (48 MB; RPC dispatch by proto index, symbols stripped by R8). **Device-observable** on `emulator-5554`: `adb install -r` arm64 APK → **Success** (distinct package from `com.ichi2.anki.debug`) → launched fresh → first-run intro → permissions → native **ankiCFA DeckPicker** (CFA / Ethics Pairs / CFA Level II decks, "23 cards due") → nav-drawer **Exam Readiness RENDERS** (source=on-device, eyebrow "ANKICFA · CFA LEVEL II", honest N/A-abstaining w/ give-up reasons, 8 canonical topics). The release build FORCED **15 genuine lint-vital fixes** in the CFA UI (HardcodedText→`@string/cfa_brand_eyebrow`; DuplicateCrowdInStrings→reuse `@string/save` + `comment=`; MenuTitleMaxLengthAttr/FixedMenuTitleLength→`maxLength="28"` + shortened `cfa_ai_fill`; UnusedResources→removed orphan + `tools:ignore` palette; DirectSystemCurrentTimeMillisUsage→`@Suppress` with a documented RPC-parity rationale) — all fixed properly, **NOT baselined**; the **19 `*Cfa*` unit tests + `lintVitalFullRelease` stay green**. Honest: signed with the fallback TEST keystore (not a Play upload key — release signingConfig reads KEYSTOREPATH/PWD/ALIAS env for a real store build); per-ABI APKs (no AAB this pass). Mobile branch `gnhf/speedrun-mobile`, evidence `AnkiDroid: proof/gnhf-speedrun/L3/packaged-build.txt` + `packaged-build/` (01 first-run, 02 permissions, 03 deckpicker, 04 exam-readiness). **Mobile Phase A (M1–M5) COMPLETE.** |

## Phase B — UI/UX passes (≥3, escalating; both apps)
| Pass | Desktop | Mobile | Log |
|------|---------|--------|-----|
| 1 (critical) | DONE (CFA web 5 MAJOR + 4 MINOR fixed; Qt chrome → Pass 2) | DONE (all 7 MAJORs fixed) | `UI-CRITIQUE-LOG.md` Pass 1 |
| 2 (harsher) | DONE (D7 Connect/Logout — named must-fix — FIXED; D9 populated render; D3 Deadline; D4 Ethics reviewer gold-phrase ladder FIXED; D6 AI Settings dialog redesigned FIXED; D8 deck-browser stock-blue leak FIXED; D11 CFA menu grouped into labelled sections FIXED — every D1–D11 surface captured+critiqued) | DONE (M6-1 DeckPicker stock-blue leak FIXED; M7-1 Readiness abstain triple-repeat FIXED; M4-2 Exam-Config context line + live countdown FIXED; M8-1 Reviewer "Show answer" CTA stock-blue→navy FIXED — every mobile surface captured+critiqued) | `UI-CRITIQUE-LOG.md` Pass 2 |
| 3 (ruthless) | DONE (D-P3-1 text contrast + D-P3-2 non-text contrast + D-P3-3 use-of-color/CVD — all FIXED; 26+10 vitest + e2e guards) | DONE (M-P3-1 WCAG AA contrast → accent-ink/on-navy, 10-test guard; M-P3-2 screen-reader grouping — Readiness cards/rows fragment for TalkBack → coherent content-desc; M-P3-3 false-affordance/touch-target — inert exam-date box → tappable 48dp control opening the picker, redundant "Pick date" button removed, 11-test guard + device-observable before/after; all FIXED) | `UI-CRITIQUE-LOG.md` Pass 3 |

Phase B kicked off (iter 25). `proof/friday/UI-INVENTORY.md` (every desktop +
mobile screen/state) and `proof/friday/UI-CRITIQUE-LOG.md` created.

**Pass 1 desktop — started (not complete):**
- **Named must-fix "Readiness does nothing" → RESOLVED + regression-guarded.**
  `ts/tests/e2e/cfa_readiness_render.test.ts` (3 tests, green) boots the real
  backend and asserts `/cfa-readiness/{deckId}` + `/cfa-home` render the three
  honest scores, the honest hero, and the full per-topic **coverage map** (all
  10 canonical CFA areas + real exam weights) bound to real data, plus the
  empty-deck path renders. Before/after screenshots in
  `desktop-ui/pass-1-before/` + `desktop-ui/pass-1/`.
- Pass-1 critique logged (D1 Home, D2 Readiness) with severities. Fixed this
  pass: D2-3 (caption "as of —" placeholder), D2-4 (deterministic topic sort);
  drive-by un-nested a pre-existing `no-nested-ternary` eslint failure in
  `home.ts` so `check:eslint`/svelte/tsc are green.
- **ALL 5 Pass-1 desktop MAJORs FIXED (iter 26)** — D1-1/D1-2/D1-3/D2-1/D2-2:
  the abstain state no longer shouts in warn-orange. Added a `muted` `CfaTone`;
  `bandValue`→ quiet "Awaiting reviews" + `bandTone`→ `muted` (down-sized 22px
  faint grey, reason in sub); the "Not enough data" verdict is said **once** in
  the Readiness hero; the unset-exam Home countdown is now neutral navy so the
  peach primary CTA is the single warm accent. Re-captured `desktop-ui/pass-1/`
  (before/after vs `pass-1-before/`); `test-e2e` **6/6 green**,
  `check:eslint`/svelte/tsc green.
- **Honesty:** GPT-4o vision CRITIC is UNAVAILABLE (no `OPENAI_API_KEY`/`.env`);
  critique is a labelled structured senior-designer heuristic pass, not a
  fabricated model transcript.
- **ALL Pass-1 desktop MINORs FIXED (iter 30)** — D1-4 (CTA-grid asymmetry →
  full-width primary + clean 2×2), D1-5 (mixed footer affordances → both pills),
  D1-6 (dense methodology paragraph → `<details>` "How these scores work"
  disclosure), D2-5 (flat 10-row "no data" table → a calm hint line above the
  map). New vitest `ts/lib/cfa/pages/readiness.test.ts` (5 tests green) locks
  `noRecallYet`/`topicRows`/`captionText`; re-captured `desktop-ui/pass-1/01` +
  `02`; `test-e2e` cfa_readiness_render 3/3, `check:eslint`/svelte/tsc green.
  **Every CFA-web-page Pass-1 desktop issue (5 MAJOR + 4 MINOR) resolved** — the
  CFA Home + Exam Readiness web surfaces are Pass-1 complete.
- **Deferred to the escalating Pass 2/3:** Qt-chrome native surfaces (D3 Deadline,
  D4 Ethics reviewer, D6 AI Settings, **D7 Connect/Logout — the objective's named
  clunky controls**, D8 deck browser, D11 chrome) via `screencapture`; a populated
  (non-abstain / Bayesian-call) render of D1/D2; then Pass 2 (harsher) + Pass 3
  (ruthless) for BOTH apps.

**Pass 1 mobile — started (capture + critique DONE, fixes TODO):**
- 7-screen "before" set captured on `emulator-5554` via `adb screencap` (real
  running debug build), committed on `gnhf/speedrun-mobile` at
  `AnkiDroid: proof/gnhf-speedrun/mobile-ui/pass-1-before/` (DeckPicker, nav
  drawer, Exam Readiness top+bottom, Exam Config, Reviewer question+answer).
- Structured senior-designer critique logged in `UI-CRITIQUE-LOG.md` (§Pass 1
  MOBILE): **7 MAJORs + 8 MINORs, 0 BLOCKERs**. Headline: the CFA activities are
  branded but the **shell (DeckPicker, nav drawer, Reviewer) is stock AnkiDroid
  light-blue** — the "non-native-CFA feel" the objective flags. Two mobile MAJORs
  (M3-1 abstain shouts in `cfa_warn`; M3-2 accent==warn) are the *same* defects
  already fixed on desktop; plus junk test decks "h"/"h gg" (M1-2).
- **CFA-activity MAJORs FIXED (iter 28)** — M3-1 (abstain warn→muted calm
  "Awaiting reviews"), M3-2 (accent==warn collision resolved), M3-3 (all three
  score cards share one rounded surface container via new
  `drawable/cfa_score_card_bg`), and M4-1/M3-6 (new `Widget.Cfa.Button.Outlined`
  navy style on both CFA outlined buttons). Device-observable after set on
  `emulator-5554` at `AnkiDroid: proof/gnhf-speedrun/mobile-ui/pass-1/`
  (03 readiness top, 04 readiness bottom, 05 exam-config). Green after the
  change: `ktlintCheck`, `lintVitalFullRelease`, CFA unit tests
  (`testPlayDebugUnitTest --tests "com.ichi2.anki.cfa.*"`).
- **SHELL REFACTOR DONE (iter 29 — the objective's flagged "biggest lift"):**
  the whole AnkiDroid shell derives from `theme_light.xml` `colorPrimary`, so
  re-branding it `cfa_navy` (the shipped default day theme) re-themes the
  DeckPicker toolbar + status bar (M1-1), Reviewer chrome + count bar
  `cfa_surface` (M5-1), tab bar/action mode and the status-bar band (M3-4) in
  one place; `fab_normal`→`cfa_accent`/`fab_pressed`→`cfa_accent_hover` makes the
  `+`/Study FAB the single warm accent (M1-3); `view_navdrawer_header.xml` is now
  a navy CFA brand lockup ("ankiCFA" + "CFA LEVEL II · EXAM PREP", no image) and
  `drawer_item_text_light.xml` selected-item colour is `cfa_navy` (M2-1); the
  junk scratch decks "h"/"h gg" were deleted from the device collection (M1-2).
  Device-observable after set `AnkiDroid: proof/gnhf-speedrun/mobile-ui/pass-1-shell/`
  (before = `pass-1-before/`). Green: `lintVitalFullRelease`, `ktlintCheck`, CFA
  unit tests. **All 7 Pass-1 mobile MAJORs resolved** → mobile Pass 1 complete.
  (Files edited on `gnhf/speedrun-mobile`, committed manually — orchestrator does
  not touch the mobile repo.)
- **TODO next:** desktop Pass-1 MINORs + Qt-chrome surfaces; then the escalating
  Pass 2 (harsher) and Pass 3 (ruthless) critiques for BOTH apps.

**Pass 2 desktop — started (iter 31): named must-fix "clunky Connect/Logout".**
- **D7 Connect/Logout FIXED** — the top bar showed **three** always-visible sync
  links (`Sync` + `Connect` + `Log out`) regardless of state (Connect present
  when already connected, Log out present when logged out — two dead in any
  state). Replaced with **one context-aware account control**
  (`Toolbar._create_account_link` → pure `cfa_sync_connect.account_link_spec`):
  logged-out → `Connect`, logged-in → `Log out` (tooltip names the account),
  keyed off `pm.sync_auth()`; `connect_cfa_sync`/`logout_of_sync` now
  `toolbar.draw()` so it flips instantly. Rendered as a distinct bordered chip
  (`#cfa_account`) set apart from the nav links (D7-2). +6 tests in
  `test_cfa_toolbar.py` (25/25 green with menu+chrome), ruff clean. Before/after
  `desktop-ui/pass-2-before/` + `desktop-ui/pass-2/` (logged-out + logged-in).

**Pass 2 desktop — POPULATED render (iter 32): the returning-learner state.**
- **D9 populated render DONE** — Pass 1 only captured the zero-review ABSTAIN
  state; the named must-fix asks for the pages to render the three scores,
  **RANGES**, and coverage map with **REAL data**. Added `tools/cfa/seed_reviews.py`
  (seeds a graded history that crosses every give-up threshold on the real
  shared engine — 320 graded reviews / 80 first exposures / 100% coverage) + a
  `CFA_SEED_REVIEWS` hook in `qt/tests/launch_anki_for_e2e.py` +
  `ts/tests/e2e/cfa_readiness_populated.test.ts` (2 green). Captured
  `desktop-ui/pass-2/01-cfa-home-populated.png` + `02-cfa-readiness-populated.png`:
  Memory 77%–81%, Performance 59%–79%, Readiness 42%–92%, hero "likely pass
  p=0.59", per-topic recall spans 69%–92% (realistic spread, not a fake flat
  100% — D9-2). Ranges stay honestly labelled ("not validated against real exam
  data"), computed with NO AI. Verify: `just cfa-seed-reviews-test` (7 green),
  `just cfa-capture-populated`; the Pass-1 abstain gate `cfa_readiness_render`
  stays green unseeded (3/3). Evidence `desktop-ui/pass-2/populated-render.txt`.

**Pass 2 desktop — DEADLINE planner captured + fixed (iter 33).**
- **D3 Deadline planner** (`/cfa-deadline/{deckId}` → `CfaDeadlinePage.svelte`) —
  a shipped desktop surface that had **never been captured/critiqued** in any
  pass. Captured both states (real backend) and fixed **D3-1 (MAJOR)**: a fresh
  all-new deck rendered **50 identical warn-orange `0.0%` rows** (a wall of
  alarming orange + misleading, since a never-studied card has no memory model so
  its 0.0 is a placeholder-by-construction, not a real recall). The payload now
  flags `isNew` (deck `is:new` set) and never warn-colours a data-less row; the
  page renders new cards as a **calm muted "New"** + en-dash interval + a one-line
  explanatory hint, while genuinely at-risk **studied** cards keep the
  `recall < 0.85` warn semantic. New `ts/lib/cfa/pages/deadline.ts` +
  `deadline.test.ts` (7 vitest) + `ts/tests/e2e/cfa_deadline_render.test.ts`
  (2 e2e, asserts zero warn rows + "New" + hint on the fresh deck). Before/after
  `desktop-ui/pass-2-before/03,04` + `pass-2/03,04`. Green: `check:vitest` 62/62,
  eslint/svelte/tsc, `ruff` on `mediasrv.py`.

**Pass 2 desktop — ETHICS reviewer captured + fixed (iter 35).**
- **D4 Ethics minimal-pairs reviewer** (`cfa/ethics_pairs/templates/front.html` +
  `style.css`) — the product's **flagship CFA learning card**, and a real
  inventory gap: never captured/critiqued in any Phase-B pass. Captured all three
  states (fresh / partial / fully-correct) via `tools/cfa/render_pairs_attempt.py`
  (a genuine end-to-end attempt driven by the REAL shared front-template JS
  grader, screenshot with `chrome-devtools-axi`). Fixed **D4-1 (MAJOR)**: on the
  graded reveal the gold answer-key phrase outlined **every** word-token with a
  full four-sided box, so a multi-word decisive phrase rendered as a **ladder of
  disconnected green word-boxes** (interior vertical dividers per word). Fix
  composes the outline from four inset **edge** rules and **opens the interior
  edges between contiguous gold tokens** (`.cfa-tok.gold + .cfa-tok.gold` /
  `:has(+ .cfa-tok.gold)`) so a phrase reads as ONE continuous outlined span while
  a lone token stays a rounded pill; night-mode mirrored. CSS-only (the
  byte-mirrored shared JS grader is untouched). New `test_gold_outline_css.py`
  (5 tests) + full ethics suite **121 passed, 3 skipped** (`test_highlight.py`
  byte-mirror green). Before/after `desktop-ui/pass-2-before/d4-ethics-*` →
  `pass-2/d4-ethics-*` (+ `d4-ethics-reviewer.txt`).

**Pass 2 desktop — AI SETTINGS dialog captured + redesigned (iter 37).**
- **D6 AI Settings** (`qt/aqt/cfa_ai_settings.py` → `CfaAiSettingsDialog`) — the
  native Qt AI on/off control, a real inventory gap never captured in any pass.
  Was a bare 3-checkbox stack + dense grey paragraph with no CFA identity and no
  indication of whether AI would actually run. **FIXED** three MAJORs: D6-1 added
  the CFA brand heading (eyebrow "ankiCFA · AI" + serif title); D6-2 grouped the
  two per-feature switches into one indented "PER FEATURE" container that greys
  out as a group under the master; D6-3 added a **live key-status line** (green
  "OpenAI API key detected — AI runs…" vs orange "No OpenAI API key set — every
  feature runs its offline fallback", via `cfa.ai.llm_client.key_present()`, key
  never shown) + D6-4 spacing/divider polish. Offscreen `QDialog.grab()` captures
  `desktop-ui/pass-2-before/d6-ai-settings-*` → `pass-2/d6-ai-settings-*`
  (master-on / master-off / key-present) via `just cfa-capture-ai-settings`.
  Verify: `just cfa-ai-settings-test` (8 green: 5 prior + 3 new); broader CFA qt
  suite 39 green; ruff clean; parity-gated `cfa_style` TOKENS unchanged. Evidence
  `desktop-ui/pass-2/d6-ai-settings.txt`.

**Pass 2 desktop — DECK BROWSER captured + fixed (iter 38).**
- **D8 Deck browser** (main-window deck list; stock `DeckBrowser` webview
  re-skinned by `qt/aqt/cfa_chrome.py`) — a Still-TODO Pass-2 surface **never
  captured/critiqued** in any prior pass. Captured the exact webview surface
  (compiled base `deckbrowser.css` + live `_deckbrowser_css()` + banner over a
  realistic CFA deck tree) and fixed **D8-1 (MAJOR)** — the desktop parallel of
  the mobile M6-1 defect: filtered/dynamic deck **names** leaked stock blue
  (`--fg-link` #1d4ed8, its `.filtered !important` beat the CFA rule) and the
  **"New" counts** leaked stock blue (`--state-new` #3b82f6). `_deckbrowser_css()`
  now retones both to brand navy (`a.deck` / `a.deck.filtered` / `.new-count`,
  all `!important` to win Anki's cascade); learn=red / review=green count
  semantics kept (M5-2/M6-1), orange accent stays the single warm accent;
  presentation-only, no token value change. New `tools/cfa/render_deck_browser.py`
  + `just cfa-capture-deck-browser` / `cfa-chrome-test`. Before/after
  `desktop-ui/pass-2-before/d8-deck-browser.png` → `pass-2/d8-deck-browser.png`
  (+ `d8-deck-browser.txt`). Verify: `test_cfa_chrome.py` **7 green** (5 prior +
  2 new), broader CFA qt suite **27 green**, ruff clean.

**Pass 2 desktop — CFA MENU (D11 window chrome) captured + fixed (iter 39).**
- **D11 CFA menu** (`aqt.cfa.setup_menu` → the "CFA" menu on the main-window
  menu bar) — the desktop "window chrome (menus/title bar)" surface, the last
  Still-TODO Pass-2 item, **never captured/critiqued** in any prior pass.
  Captured (offscreen `QMenu.grab()` via `tools/cfa/render_cfa_menu.py`, the
  same real menu the unit test builds) and fixed **D11-1 (MAJOR)**: the eight
  actions were a flat undifferentiated list (dashboard + report + 3 study modes
  + settings + 2 account controls as sibling rows). Now grouped into three
  **labelled native sections** via `addSection` — **Dashboard** / **Study
  modes** / **Settings & account** — that degrade to plain separators where
  section text isn't rendered; plus **D11-2 (MINOR)** a `setStatusTip` on every
  command for hover discoverability. Structure-only (no handler/token change).
  Before/after `desktop-ui/pass-2-before/d11-cfa-menu.png` →
  `pass-2/d11-cfa-menu.png` (+ `d11-cfa-menu.txt`). New recipe
  `just cfa-capture-cfa-menu`. Verify: `just cfa-menu-test` **13 green** (11
  prior + 2 new section-structure tests); menu+toolbar+chrome **29 green**;
  `ruff` clean. **With D11, every inventoried desktop surface (D1–D11) is
  captured+critiqued and all MAJORs fixed → Phase B Pass 2 desktop COMPLETE.**

**Pass 2 mobile — started (iter 34): DeckPicker stock-blue leak (M6-1).**
- After the Pass-1 shell refactor branded the shell navy, the harsher Pass-2
  lens found TWO residual stock-AnkiDroid blue tokens leaking on the primary
  landing screen (DeckPicker): filtered/dynamic **deck names** (`dynDeckColor`
  `#2222bb`) and the **"new" card counts** (`newCountColor`
  `material_indigo_700`). **FIXED (M6-1, MAJOR)** — both retoned to
  `@color/cfa_navy` in `theme_light.xml`; the deck list now reads as one cohesive
  navy CFA list (learn=red/review=green count semantics kept, orange FAB the
  single accent). Device-observable before/after on `emulator-5554`
  (`AnkiDroid: proof/gnhf-speedrun/mobile-ui/pass-2-before/01` →
  `pass-2/01` + `02` + `deckpicker-brand.txt`). Green:
  `installFullDebug`, `lintVitalFullRelease`, `ktlintCheck`. Committed on
  `gnhf/speedrun-mobile` (orchestrator does not touch the mobile repo).

**Pass 2 mobile — READINESS abstain triple-repeat fixed (iter 40): M7-1.**
- The flagship **Exam Readiness** screen (`CfaExamReadinessActivity`) re-captured
  under the harsher Pass-2 lens. In the awaiting-data state all three honest score
  cards rendered the shared engine's give-up `reason` verbatim, and the engine's
  READINESS reason is a literal concatenation of the memory + performance reasons —
  so the hero card repeated the SAME counts already shown on the two cards below AND
  in the evidence caption (the user read the same numbers **three times**). **FIXED
  (M7-1, MAJOR)** — when both inputs abstain, the hero card shows a concise composite
  sub-line (`cfa_readiness_abstain_hint`) via a new `abstainOverride` param on
  `scoreCard()`, instead of the verbatim reason; the specific counts stay honest +
  visible on the Memory/Performance cards and the caption. Presentation-only (the
  shared `computeCfaScores` RPC, the abstain rule, and every count untouched). Same
  defect the desktop team fixed in iter 26 ("state the verdict once"). Device-observable
  before `pass-2-before/03-readiness-repeat.png` → after
  `pass-2/03-readiness-deduped.png` (+ `pass-2/readiness-dedup.txt`). Green:
  `installFullDebug`, `ktlintCheck`, `lintVitalFullRelease`, CFA unit tests. Committed
  on `gnhf/speedrun-mobile`. (Carried Pass-1 MINOR M2-2 also confirmed resolved — the
  Exam Readiness nav-drawer entry already uses the `ic_cfa_readiness` bar-chart icon.)

**Pass 2 mobile — EXAM CONFIG context + countdown (iter 41): M4-2.**
- The **Exam configuration** screen (`CfaExamConfigActivity`) re-looked under the
  harsher Pass-2 lens: it was a bare title + "No exam date set" field + Pick date
  + Save over a ~60% empty screen, with no rationale and no feedback after picking
  a date. **FIXED (M4-2, carried Pass-1 MINOR)** — added a calm `cfa_muted`
  **context line** ("Set your exam date so ankiCFA can weight study by
  points-at-stake and show a live countdown on the Exam Readiness screen.") and a
  **live countdown preview** in warm `cfa_accent` ("N days to the exam" via a
  `plurals`, today/past special cases, hidden when unset), backed by a pure
  unit-tested `CfaExamConfig.daysUntil(date, today)`. Presentation-only — the
  synced `cfa_exam_config` col.conf shape is untouched. Device-observable before
  `pass-2-before/05-exam-config-sparse.png` (genuine pre-fix on the current navy
  shell) → after `pass-2/05-exam-config-context.png` + `06-exam-config-countdown.png`
  (+ `pass-2/exam-config-density.txt`). Green: `CfaExamConfigTest` **7 tests**
  (3 prior + 4 new `daysUntil`), `ktlintCheck`, `lintVitalFullRelease`,
  `installFullDebug`. Committed on `gnhf/speedrun-mobile`.

**Pass 2 mobile — REVIEWER "Show answer" CTA branded (iter 42): M8-1 → Pass 2 mobile COMPLETE.**
- The **Reviewer** (`Reviewer`/`AbstractFlashcardViewer` +
  `include_reviewer_answer_buttons.xml`) — the highest-time-on-screen surface —
  re-looked under the harsher Pass-2 lens. Pass 1 branded its toolbar navy and
  count bar `cfa_surface`, but the single **primary CTA** ("Show answer") was
  still stock: the legacy flip button reused `@style/HardButton` +
  `?attr/hardButtonRef` (both resolve to the stock blue-grey Hard ease colour
  `material_blue_grey_700`; the animation path via `footer_button_ripple` reads
  `answerButtonBackground` off the view theme → blue-grey too), and the new
  reviewer's `showAnswerButtonBackground` was stock `material_blue_700`.
  **FIXED (M8-1, MAJOR)** — new `drawable/footer_button_showanswer` (navy) + new
  `@style/CfaShowAnswerButton` (`answerButtonBackground=cfa_navy`, so BOTH the
  static and ripple paths render navy); `flashcard_layout_flip` retargeted to
  them; `theme_light.xml showAnswerButtonBackground`→`cfa_navy`. The "Show
  answer" CTA is now brand navy, matching the toolbar; the four-grade ease
  buttons (again=red/hard=blue-grey/good=green/easy=light-blue) are **unchanged**
  (verified). Device-observable before `pass-2-before/07-reviewer-showanswer-bluegrey.png`
  → after `pass-2/07-reviewer-showanswer-navy.png` + `08-reviewer-ease-buttons-intact.png`
  (+ `pass-2/reviewer-showanswer.txt`). Green: `installFullDebug`, `ktlintCheck`,
  `lintVitalFullRelease`, CFA unit tests. Committed on `gnhf/speedrun-mobile`.
  **Every inventoried mobile surface captured+critiqued, all Pass-2 MAJORs fixed
  → Phase B Pass 2 mobile COMPLETE.** Remaining: the escalating **Pass 3
  (ruthless)** for BOTH apps.

**Pass 3 desktop — started (iter 43): scientific WCAG AA contrast audit.**
- **D-P3-1 (MAJOR, accessibility) FIXED** — the ruthless pass opened with a
  *measured* WCAG 2.1 contrast audit of the CFA web tokens (ratios computed from
  the real hex values, not a by-eye critique). Finding: `$cfa-faint` (#939597),
  documented "captions / disabled", was colouring **readable text** everywhere
  (StatCard subs + "Awaiting reviews" value, Home/Readiness score-meaning lines,
  `Caption tone="faint"`, Hero sub, per-topic "no data" cell) yet fails AA —
  **3.01:1 on white, 2.90 / 2.77 on the page / surface tints (below even the 3:1
  large-text floor)**. Parity-safe fix (iter-26 pattern): demote `$cfa-faint` to
  decorative-only (value untouched → `cfa_style.py` stays byte-identical; desktop
  uses it as a bg, not text) and add a new web-only AA-safe tertiary-**text**
  token **`$cfa-faint-ink` (#68707d)** — AA body on all three backgrounds
  (5.00 / 4.83 / 4.60), lighter than `$cfa-muted` so the `ink > muted >
  faint-ink` hierarchy holds. Repointed 8 text usages. New
  `ts/lib/cfa/contrast.test.ts` (**16 vitest, green**) parses the tokens and
  asserts AA + a regression guard that fails if `color: cfa.$cfa-faint` (text)
  ever returns. Full CFA vitest **28/28**; `check:svelte`/`typescript`/`eslint`
  green; both populated e2e specs 2/2. Before/after +
  `03-contrast-audit-proof.png` under `desktop-ui/pass-3{,-before}/` +
  `contrast-audit.txt`.
- **D-P3-2 (MAJOR, accessibility) FIXED (iter 45)** — the ruthless lens extended
  the *measured* method to **WCAG 2.1 SC 1.4.11 Non-text Contrast** (the boundary
  that makes a control perceivable, not just text). Finding: the secondary Study
  CTAs, footer chips and the Deadline date input have a **white fill on the
  near-white page** and draw their only edge with the decorative hairline
  `$cfa-line` (#e7e9ec) — **1.22:1 on white / 1.17 / 1.12** vs the **3:1** a
  control boundary needs, so they **float invisibly**. Parity-safe fix: a new
  web-only **`$cfa-control-border` (#7e8896)** clears 3:1 as an edge on all three
  backgrounds (**3.59 / 3.47 / 3.31**) while staying lighter than `$cfa-muted`;
  repointed the 3 interactive controls, decorative hairlines untouched.
  `ts/lib/cfa/contrast.test.ts` **16 → 21 vitest (green)** with a 1.4.11 audit
  block + regression guard; full CFA vitest **33/33**;
  `check:svelte`/`typescript`/`eslint` green. Device-observable before/after
  (same populated seed, stash-isolated) + `03-nontext-contrast-proof.png` under
  `desktop-ui/pass-3-nontext{,-before}/` + `nontext-contrast.txt`.
- **D-P3-3 (MAJOR, accessibility) FIXED (iter 46)** — the ruthless lens moved
  from contrast *ratios* to the *channel* question and applied **WCAG 2.1 SC
  1.4.1 Use of Color (Level A)**. Finding: the Deadline planner flagged an
  at-risk row (studied card, predicted exam-day recall < 0.85) by colouring the
  figure warn-orange and **nothing else** — `recallCell()` returned the same
  "62.1%" string, so colour was the SOLE cue (invisible to ~8% of men with a
  red-green CVD). Scientific grounding: **simulated dichromacy** (Viénot
  severity-1 matrices in linear RGB → CIE76 ΔE) shows the pass↔warn hue pair
  **collapses 84→15 ΔE under protanopia** (>65% lost); honestly the warn-vs-ink
  pair in this table keeps luminance separation, so it's a Level-A compliance
  gap, fixed regardless. Fix: a redundant **non-colour shape marker "▲"** before
  the figure (new `isAtRisk`/`riskMarker` helpers) + a visually-hidden
  screen-reader "at risk:" label (`.cfa-deadline__sr`); new cards never carry it;
  warn colour kept for sighted users. `deadline.test.ts` **7→10**,
  `contrast.test.ts` **21→26** (a 1.4.1 audit block: CVD sanity, asserted
  pass/warn collapse, honest warn/ink retention, FIX + regression guard), and a
  new REAL-backend e2e gate `cfa_deadline_colorcue.test.ts` (every warn cell also
  carries ▲, count-matched). Full CFA vitest **41/41**; `./ninja check:svelte
  check:typescript check:eslint` green. Genuine before/after (seeded, scrolled to
  the at-risk rows, stash-isolated) + `colorcue-audit.txt` under
  `desktop-ui/pass-3-colorcue{,-before}/`.

**Pass 3 mobile — started (iter 44): scientific WCAG AA contrast audit.**
- **M-P3-1 (MAJOR, accessibility) FIXED** — the ruthless mobile pass opened with
  the same *measured* WCAG 2.1 audit applied to the CFA Android tokens (ratios
  computed from the compiled `R.color` values). Finding: the warm brand accent
  `cfa_accent` (#DA5C01) was colouring small readable TEXT — the Readiness &
  Config eyebrows (11sp), the exam countdown (13sp) on white and the nav-drawer
  tagline (12sp) on navy — yet only reaches **3.81:1 on white / 3.78:1 on navy**,
  below AA's 4.5:1 (the desktop design system already dodges this by using an
  AA-safe green eyebrow, `Eyebrow.svelte` #007e56, not the orange accent).
  Parity-safe fix (accent VALUE unchanged → still correct for the FAB tint /
  outlined-button ripple / progress indicator): two AA-safe accent-**text**
  tokens in `res/values/cfa.xml` — **`cfa_accent_ink` #A84500** for light
  backgrounds (white 5.97 / surface 5.50) and **`cfa_accent_on_navy` #F0894A**
  for the navy drawer (5.74); darkening reduces navy contrast, so navy needs a
  brighter tint (hence two tokens). Repointed the 4 TextViews. New
  `CfaContrastTest.kt` (**10 tests, green**) computes contrast from the compiled
  resources, asserts AA on every background, documents why the raw accent fails,
  and a regression guard that parses the layouts and fails if `cfa_accent`
  returns as a text colour. Device-observable before/after (stash-isolated) +
  `04-contrast-audit-proof.png` under `AnkiDroid: proof/gnhf-speedrun/mobile-ui/pass-3{,-before}/`
  + `contrast-audit.txt`. Green: CFA unit tests, `lintVitalFullRelease`,
  `ktlintCheck`, `installFullDebug`. Committed on `gnhf/speedrun-mobile`
  (`ff9a2632b5`).
- **M-P3-2 (iter 47):** screen-reader grouping — the Exam Readiness score cards
  and per-topic rows fragmented into disconnected TalkBack nodes; fixed with
  coherent `contentDescription`s + focus grouping (WCAG 1.3.1/4.1.2), 7-test
  guard + `uiautomator` before/after dumps.
- **M-P3-3 (iter 48) — Pass 3 mobile COMPLETE:** the Exam Config **date box was
  a false affordance** — styled as a filled input but inert, with the only
  picker trigger on a separate "Pick date" button. Made the box the tappable
  control (clickable/focusable, 48dp Material/WCAG-2.5.5 touch target, ripple,
  calendar affordance, coherent TalkBack label via a new pure
  `examDateFieldContentDescription`) and **removed the redundant button**.
  `CfaAccessibilityTest` **7→11** (3 pure + a layout/source regression guard);
  device-observable before (`clickable=false`, empty content-desc, button
  present) → after (`clickable=true`, coherent content-desc, no button, **tap
  opens the picker**) under `mobile-ui/pass-3{,-before}/` + `affordance-audit.txt`.
  Green: CFA unit tests, `ktlintCheck`, `lintVitalFullRelease`, `installFullDebug`.
  **Both apps now have 3 ruthless Pass-3 findings, all MAJOR, all FIXED with
  passing tests + genuine before/after evidence → Phase B Pass 3 COMPLETE.**

Named must-fix: desktop Readiness renders with data (**functional gate DONE** +
**populated real-range render DONE, iter 32**); **Connect/Logout redesigned
(DONE, iter 31)**; native-CFA feel everywhere (desktop shell chrome WIP; mobile
shell DONE); AnkiDroid CFA UI full refactor (Pass 1 DONE).

## Final VERIFIER pass (iter 49) — stop condition reconfirmed GREEN
Re-ran the targeted cfa tests + rebuilt the desktop stack from a clean check
after Phase B completed; every gate green, so the run's stop condition is met.
- **Targeted cfa tests (desktop worktree):** `cfa-eval-test` **67**, `cfa-outline-test`
  **11**, `cfa-model-docs-test` **5**, `cfa-rust-note-test` **6**, `cfa-results-test`
  **5**, `cfa-scores-test` **10**, `cfa-parity-test` **2**, `cfa-chrome-test` **7**,
  `cfa-menu-test` **13**; CFA vitest (`contrast`/`deadline`/`readiness`) **41** — all pass.
- **Desktop build green:** web stack builds (`rebuild-web` "Build succeeded"; the
  trailing Chromium-remote-debugger error is the documented harmless hot-reload
  probe — Anki not open) and the shared Rust backend compiles clean with
  `scheduler::cfa_scores` **3/3** passing.
- **Mobile build green:** unchanged since iter 48's green reconfirmation — mobile
  `HEAD` is still `85ef4fc718` (zero mobile commits since; `installFullDebug` /
  `lintVitalFullRelease` / `ktlintCheck` / CFA unit tests were green at that SHA).
- **Evidence present:** desktop **43** before/after PNGs across pass-1/2/3
  (+ nontext/colorcue variants); mobile **41** committed PNGs across
  pass-1/1-before/1-shell/2/2-before/3/3-before, plus the M1–M5 L3 device-proof
  dirs — before/after captured for every inventoried screen on both apps.
- **Conclusion:** Phase A (A1–A14 + M1–M5) all DONE with tests/evidence; Phase B
  ran **3 escalating passes for BOTH apps**, all BLOCKER/MAJOR issues fixed and
  logged in `UI-CRITIQUE-LOG.md`; targeted cfa tests + both builds green. **Stop
  condition fully met.**
