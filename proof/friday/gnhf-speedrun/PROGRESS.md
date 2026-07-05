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
| 2 (harsher) | WIP (Qt chrome: D7 Connect/Logout — named must-fix — FIXED) | TODO | `UI-CRITIQUE-LOG.md` Pass 2 |
| 3 (ruthless) | TODO | TODO | |

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

Named must-fix: desktop Readiness renders with data (**functional gate DONE** +
**populated real-range render DONE, iter 32**); **Connect/Logout redesigned
(DONE, iter 31)**; native-CFA feel everywhere (desktop shell chrome WIP; mobile
shell DONE); AnkiDroid CFA UI full refactor (Pass 1 DONE).
