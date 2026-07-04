# CFA Speedrun — Single GNHF Run: MASTER PLAN (features → UI/UX)

> One long GNHF run. Desktop = this repo. Mobile = `/Users/adarshrajesh/wed/AnkiDroid`.
> Do **Phase A (every feature)** fully, committing each, **then** the big
> **Phase B (UI/UX critique loop)**. Track everything in
> `proof/friday/gnhf-speedrun/PROGRESS.md` (update after each item).

## 0. Mission & the honesty rule

A **CFA Level II exam-prep app built on Anki** — a native CFA product, not "Anki
with a CFA tab." Answer three *separate* questions, each with a range: **Memory**,
**Performance**, **Readiness**. **Honesty rule (non-negotiable):** never print or
show a number without the evidence behind it; label any synthetic/simulated data
`SIMULATED`; keep the give-up rule (abstain when data is insufficient); the app
must still produce a score with **AI switched off**. Fabricating or dressing up a
guess as a measurement is an automatic fail.

## 1. Roles & personalities (you orchestrate; spawn sub-agents)

- **YOU = "THE PERFECTIONIST"** — lead product engineer with an obsessive,
  UWorld-grade bar. Nothing clunky ships. Every claim is verified with a test or a
  screenshot. You never mark an item done without committed evidence. "Good enough"
  is never good enough.
- Spawn sub-agents with **explicit roles**:
  - **IMPLEMENTER** — builds one feature end-to-end + a test, then commits.
  - **CRITIC / EVALUATOR** — a ruthless senior product designer + QA lead from a
    top paid exam-prep company (think UWorld). Screenshots every screen and state,
    critiques it mercilessly against the rubric (§4), files issues with severity.
    **Gets harsher every pass.** Assume this is a premium paid product.
  - **VERIFIER** — runs tests/builds, confirms evidence files exist, and **rejects**
    any unsubstantiated "done."
- Parallelize independent work via sub-agents, but never let two agents edit the
  same file at once — assign disjoint file scopes.

## 2. Global rules

1. **Verify after EACH item** — a passing test (features) or a captured
   screenshot/log (UI/build items) + an evidence file — **then COMMIT**. Small,
   frequent commits so code is testable immediately.
2. **Do NOT run `no-mistakes`.** Use targeted `just cfa-*`, `pytest`, `cargo test`,
   and Gradle `*Cfa*` tests.
3. **Full autonomy / all permissions** — do not stop to ask; make the
   production-grade choice and note it in PROGRESS.md.
4. **Honesty** — never fabricate/inflate; label `SIMULATED`; AI-off must still
   score; keep the give-up rule.
5. **NO VIDEOS.** Where the spec asks for a recording, capture an **ordered
   screenshot sequence + a text log** instead (the user records the final demo
   video themselves). Save under `proof/`.
6. **Two repos.** Desktop = this repo, on your gnhf branch. Mobile =
   `/Users/adarshrajesh/wed/AnkiDroid` — create and work on branch
   `gnhf/speedrun-mobile`; commit there frequently.
7. Keep every currently-green test green.
8. Evidence roots: desktop `proof/friday/gnhf-speedrun/`; mobile
   `proof/gnhf-speedrun/` (in AnkiDroid). Keep `PROGRESS.md` current.

## 3. PHASE A — implement EVERY remaining feature (commit + verify each)

Order: **P0 first**, then P1, then P2. Already-DONE (do not redo): the 3 Rust RPCs
(BuildExamQueue/DeadlineRetention/ComputeCfaScores) + 24 Rust tests + undo-safety;
desktop AI-settings dialog + one-click Connect/Logout; three scores + ranges +
give-up (desktop & mobile); leakage check; AI-off both platforms; mobile
exam-priority (real `buildExamQueue` RPC) + exam-config + ethics deck + Tab-key AI
fill; sync engine round-trip + offline conflict + dedup.

### Desktop (this repo)

- **A1 [P0] AI beats a simpler baseline.** Add a keyword/TF-IDF (and optionally
  vector) baseline grader; a 3-way side-by-side (deterministic-span vs TF-IDF vs
  LLM) on `cfa/ethics_pairs/eval_attempts.jsonl`. New `cfa/eval/baseline_compare.py`
  + `just cfa-baseline-compare`. *Verify:* test + `L1/baseline-compare.txt`.
- **A2 [P0] Wrong-answer rate + cutoff.** In `cfa/ethics_pairs/eval_ai_grading.py`
  add a named `wrong_answer_rate` (false-accepts of human-incorrect) + gate on
  `accuracy>=A_CUT AND wrong_answer_rate<=W_CUT`. *Verify:* test + `eval-gate.txt`.
- **A3 [P1] Memory calibration (Sunday).** `cfa/eval/calibration.py`: **Brier +
  log loss + reliability chart** on held-out reviews (prefer a real revlog fixture;
  else label `SIMULATED`). `just cfa-calibration`. *Evidence:* `calibration.png`
  + `calibration.txt`.
- **A4 [P1] Performance-model accuracy (Sunday).** Predict whether the student gets
  held-out exam-style questions right (topic mastery, difficulty, timing,
  coverage); report **accuracy on held-out questions**. `cfa/eval/performance_eval.py`
  + `just cfa-performance-eval`. *Evidence:* `performance-eval.txt`.
- **A5 [P1] Paraphrase gap 7d.** `cfa/eval/paraphrase_test.py`: recall-on-card vs
  accuracy-on-reworded (30 concepts × 2), report the **memory-vs-performance gap**.
  `just cfa-paraphrase`. *Evidence:* `paraphrase-gap.txt`.
- **A6 [P1] Card-gen gold set 7f.** `cfa/eval/cardgen_gold.jsonl` (50 known-correct
  CFA QA) + `cfa/eval/cardgen_check.py`: generate 50 cards from a named source,
  bucket correct+useful / wrong / correct-but-bad, **cutoff declared up front**,
  block failures. `just cfa-cardgen-check`. *Evidence:* `cardgen-check.txt`.
- **A7 [P1] Coverage map + topics 8→10.** `cfa/outline/level2_topics.json` (10
  official areas); extend `CANONICAL_TOPICS` to 10 in **both** `pylib/anki/cfa.py`
  and `rslib/src/scheduler/cfa_scores.rs` (keep Rust==Python parity); update
  `topics_total==8` tests to 10; render a coverage map (topic→covered?→%) on the
  readiness dashboard. *Verify:* `just cfa-scores-test cfa-parity-test cfa-f4-test
  cfa-deck-test` + `coverage-map.png`.
- **A8 [P1] Study-feature ablation §8.** One feature (recommend the exam-priority
  points-at-stake queue), a one-sentence hypothesis, **3 builds** (feature ON /
  feature OFF / plain unmodified Anki) on the same cohort + questions + study-time
  budget; pre-registered metric **with a range**; report null results honestly;
  label `SIMULATED`. `tools/cfa/ablation_harness.py` + `just cfa-ablation`.
  *Evidence:* `ablation.txt`.
- **A9 [P1] One-command benchmark §10/7h.** `just bench` + `tools/cfa/bench.py`:
  ~50k-card deck, print **p50/p95/worst** for answerCard ack, next-card,
  dashboard first load, dashboard refresh, sync. `just bench-smoke` for CI.
  *Evidence:* `bench.txt`.
- **A10 [P1] Crash + offline robustness 7g.** `pylib/tests/test_cfa_crash_robustness.py`:
  kill mid-review ~20× → zero corruption (`quick_check`); plus offline + AI-off →
  still returns a score. `just cfa-crash-test`. *Evidence:* `crash-robustness.txt`.
- **A11 [P1] Score-mapping + model-description docs (Sunday).** Write the
  memory / performance / readiness **method + range + give-up rule**, one short
  page each, in `docs/cfa/MODEL-*.md`. *Evidence:* the docs + `PROGRESS.md` entry.
- **A12 [P2] Unify Rust-change note.** `docs/cfa/RUST_ENGINE_NOTE.md` covers all 3
  RPCs + why-Rust + upstream files + merge difficulty; fix stale test counts.
- **A13 [P2] Desktop installer (Sunday).** Build a packaged installer
  (`tools/build-installer`; populate mac/win submodules if feasible, else at least
  the current-platform artifact) and capture a **clean-machine install screenshot
  sequence** (no video). If signing/toolchain blocks it, keep the wheels-based
  clean-machine proof and mark `BLOCKED` with the root cause.
- **A14 [P2] Consolidated results report + Brainlift (Sunday).** Assemble all eval
  / bench / ablation / calibration numbers into `proof/friday/RESULTS-REPORT.md`
  (include results that did not work). Update `Brainlift.md` per the class outline.

### Mobile (`/Users/adarshrajesh/wed/AnkiDroid` — details in its SPEEDRUN-MOBILE-PLAN.md)

- **M1 [P0] Scores via shared Rust `computeCfaScores` RPC** (Kotlin fallback only).
- **M2 [P0] Device-observable desktop→phone reverse sync** (fix collection reset).
- **M3 [P1] Same-card offline conflict merge (Sunday 7b)** — documented, with a
  screenshot-sequence proof (not video).
- **M4 [P1] Offline-then-sync + AI-off-still-scores** — verify + screenshot proof.
- **M5 [P2] Packaged phone build (Sunday)** — signed release APK if a keystore is
  available; else assembleRelease-unsigned + `BLOCKED` note.

## 4. PHASE B — UI/UX production-grade critique loop (final, biggest goal)

Start **only after Phase A is committed.** This is a science with a fixed process.
Both apps. **At least 3 passes; each pass more critical than the last.** Fix ALL
blocker + major issues. Everything noted down.

### Process (repeat per pass, per app)
1. **Inventory** every screen + state into `UI-INVENTORY.md` (desktop: CFA Home,
   Reviewer, Ethics minimal-pairs, **Readiness**, Exam-priority, AI Settings,
   Connect/Logout, deck browser, deck config, stats, menus/toolbar, empty/loading/
   error states; mobile: DeckPicker, Reviewer, CFA Readiness, Exam Priority, Exam
   Config, Ethics, nav drawer, sync/settings, empty/loading/error).
2. **Capture** each screen/state to `…/gnhf-speedrun/<desktop-ui|mobile-ui>/pass-N/`
   — desktop: Playwright (`ts/tests/e2e/` harness) drives the CFA Svelte pages at
   `http://localhost:40000/_anki/pages/` + `screencapture -x` for Qt chrome; mobile:
   `adb exec-out screencap -p > f.png` (fallback `adb shell screencap -p
   /sdcard/s.png && adb pull`), navigate via `adb shell am start` / `input tap`.
3. **Critique (CRITIC role, GPT-4o vision)** — POST each screenshot to GPT-4o
   vision (key in `.env`) with the rubric below; get structured JSON: screen,
   element, issue, severity (blocker/major/minor), concrete fix. **Rubric:** visual
   hierarchy; spacing/alignment/grid; typography scale; color, contrast, WCAG AA;
   consistency & design-token use; affordances & discoverability; microcopy; motion;
   empty/loading/error states; information density; functional correctness; and
   "does this look like a premium paid CFA prep product." Escalate strictness each
   pass (pass 3 = ruthless, pixel-level).
4. **Log** every issue in `UI-CRITIQUE-LOG.md` (per screen, per pass).
5. **Fix (IMPLEMENTER)** ALL blocker+major issues; extend the design system
   (desktop `ts/lib/cfa` tokens; mobile a proper theme/styles + Material components).
   Commit per screen/fix. Keep feature tests green.
6. **Re-capture & re-critique** next pass; save before/after pairs.
7. **Functional gate:** for "does nothing" bugs (e.g., desktop **Readiness**),
   add a Playwright/adb check that the screen actually renders with data.

### Must-fix named issues
- **Desktop Readiness does nothing** → make it actually open and render the three
  scores + ranges + coverage map with real data; add a functional test.
- **Connect / Logout controls are clunky** → redesign into clear, discoverable,
  well-labelled states (connected/disconnected, syncing, logged-in-as).
- **Native-CFA feel everywhere** → the whole desktop shell (not just the CFA tab)
  must read as a CFA product: branding, typography, color, home, reviewer chrome.
- **AnkiDroid CFA UI full refactor** → the mobile app UI is the biggest lift;
  rebuild every CFA screen to premium production grade.

## 5. Stop condition

Every Phase A feature (desktop + mobile + Sunday deliverables) is committed with a
passing test or captured evidence and checked off in `PROGRESS.md`; **and** Phase B
has completed **≥3 increasingly-critical UI/UX passes for BOTH apps** with
before/after screenshots for every screen and **all blocker + major issues resolved
or explicitly documented** in `UI-CRITIQUE-LOG.md`; **and** the targeted cfa tests
plus the desktop and mobile builds are green. Mark any genuinely blocked item
`BLOCKED` with a root cause. Never fabricate evidence.

## 6. Tooling appendix

- **adb:** `/opt/homebrew/share/android-commandlinetools/platform-tools/adb`;
  emulator online as `emulator-5554` (AVD `ankidroid_cfa`). Start if down:
  `/opt/homebrew/share/android-commandlinetools/emulator/emulator @ankidroid_cfa &`.
- **Emulator screenshot:** `adb exec-out screencap -p > f.png` (fallback
  `adb shell screencap -p /sdcard/s.png && adb pull /sdcard/s.png f.png`).
- **Desktop web screenshots:** Playwright (`@playwright/test`, harness in
  `ts/tests/e2e/`) against mediasrv pages; `just` runs the app.
- **Qt chrome screenshots:** `screencapture -x /tmp/shot.png` while the app runs.
- **Vision critique:** GPT-4o via the OpenAI API in `.env` (dev-time tool, not a
  shipped feature). Send image + rubric, parse JSON issues.
- **AI-off contract:** unset `OPENAI_API_KEY` (or the master toggle) → deterministic
  fallback; scores must still render.
