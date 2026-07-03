# CFA Exam-Prep Pro Upgrade — Submission Checklist (F0a–F9)

Production-grade CFA exam-prep upgrade shipped **one feature at a time**, each
implemented **additively** on top of `origin/main` (`ee2f36d19`), each proven
with a passing test suite and real rendered / on-device screenshot proof, and
each validated through the **documented fallback gate** (see _Gate_ below).

Every AI feature works fully with **AI OFF** through a deterministic fallback;
no OpenAI key is committed, printed, or required to run the suite.

## How to reproduce the whole gate

```bash
# AI foundation + visible desktop fixes
just cfa-ai-smoke                                   # F0a (8 pass, 1 skip = with-key)
just cfa-f0b-test                                   # F0b (6 pass)
# Ethics one-passage multi-span + semantic grading
just cfa-passages-test  cfa-passages-validate       # F1 (29 pass · 30 passages/73 spans)
just cfa-ai-grade-test  cfa-ethics-eval             # F2 (20 pass · eval agreement 0.733 AI-off)
# AI tab-fill · honest scoring · UI overhaul
just cfa-tab-fill-test                              # F3 (18 pass)
just cfa-f4-test                                    # F4 (17 pass)
just cfa-f5-test                                    # F5 (13 pass)
# Mobile bundle · cross-platform persistence
just cfa-f7-test                                    # F7 (3 pass)
just cfa-f8-test                                    # F8 (3 pass)
# Pre-existing suites (regression — all still green)
just cfa-test cfa-menu-test cfa-seed-test cfa-scores-test \
     cfa-deck-test cfa-eval-test cfa-eval-leakage cfa-types-test cfa-sync-test
# Headline Python/Qt count — ONE deduplicated pytest collection (supersedes summing the recipes above)
just cfa-f9-test-tally                              # 203 passed, 1 skipped
# Shared Rust engine — 21 unique CFA tests via two DISJOINT scoped filters
# (the broad `-- exam` filter mis-reports 15: "exam" also matches a cfa_deadline test)
cargo test -p anki --lib -- scheduler::cfa_deadline                       # 10 pass
cargo test -p anki --lib -- scheduler::service::tests::exam_queue \
     scheduler::service::tests::verification_probe                        # 11 pass
# End-to-end reachability on a fresh seed
QT_QPA_PLATFORM=offscreen PYTHONPATH="out/pylib:pylib:qt:out/qt:cfa/ethics_pairs:." \
     out/pyenv/bin/python tools/cfa/f9_reachability.py   # F9 REACHABILITY: PASS
```

## Real numbers (this iteration)

- **Python/Qt: 203 passed, 1 skipped** — reproducible as ONE deduplicated pytest collection via `just cfa-f9-test-tally` (204 collected; the 1 skip is the with-key real-LLM smoke, honestly skipped AI-off). Composition: 116 new F-series tests + 87 pre-existing regression tests.
- **Rust (CFA-specific): 21 passed** — 10 (`cargo test -p anki --lib -- scheduler::cfa_deadline`) + 11 (`cargo test -p anki --lib -- scheduler::service::tests::exam_queue scheduler::service::tests::verification_probe`); two disjoint scoped filters, so no double-count (the broad `-- exam` filter mis-reports 15).
- **Ethics bank:** 30 one-passage items, 73 gold evidence spans, validated verbatim / token-locatable / non-overlapping.
- **Eval:** 30 human-labeled ethics attempts; AI-off deterministic grader agreement **0.733** (the LLM ≥0.80 assertion is honestly _skipped_ with no key).
- **Leakage:** clean — no held-out eval question overlaps a training-deck front (Jaccard < 0.6).
- Full logs: `proof/gnhf2/f9-full-suite.log`; reachability: `proof/gnhf2/f9-reachability.txt`.

## Feature status

| #   | Feature                                                                                                 | Gate recipe(s)                                | Result                        | Proof                                                                             | Branch SHA       |
| --- | ------------------------------------------------------------------------------------------------------- | --------------------------------------------- | ----------------------------- | --------------------------------------------------------------------------------- | ---------------- |
| F0a | AI foundation — reusable AI-off-safe OpenAI client                                                      | `cfa-ai-smoke`                                | 8 pass · 1 skip (with-key)    | `proof/gnhf2/f0a-ai-foundation.log`                                               | `326b2229b`      |
| F0b | Visible desktop fixes — on-demand ethics preload, no dead-ends, exam-date picker, honest new-card queue | `cfa-f0b-test`                                | 6 pass                        | `f0b-deadline-{default,picked}.png`                                               | `9049d92a3`      |
| F1  | Ethics one-passage multi-span redesign (30 passages, 73 spans) + deterministic grader Py↔JS             | `cfa-passages-test` / `cfa-passages-validate` | 29 pass · bank valid          | `f1-psg17-fullycorrect.png`, `f1-psg04-partial.png`                               | `0b8ef5d37`      |
| F2  | Semantic AI grading of ethics highlights + AI-off fallback + 30-item eval                               | `cfa-ai-grade-test` / `cfa-ethics-eval`       | 20 pass · agreement 0.733     | `f2-psg01-ai.png`, `f2-psg01-aioff.png`, `f2-eval-report.txt`                     | `03177a29c`      |
| F3  | AI tab-to-fill card backs (provenance tag, overwrite guard, AI-off disabled)                            | `cfa-tab-fill-test`                           | 18 pass                       | `f3-tab-fill.png`                                                                 | `683d63314`      |
| F4  | Honest scoring redesign — SM-2 recall fallback + 95% credible band + explicit pass/fail call            | `cfa-f4-test`                                 | 17 pass                       | `f4-readiness-{sparse,strong,weak}.png`                                           | `272352c12`      |
| F5  | UI overhaul — shared CFA design system (Mark-Meldrum calm finance aesthetic)                            | `cfa-f5-test`                                 | 13 pass                       | `f5-{readiness,deadline,ethics-card}-{before,after}.png`                          | `aa759dc44`      |
| F6  | Android shared engine repoint — fork Rust engine runs on-device                                         | on-device (adb)                               | fork RPC loads on device      | `f6-ondevice-deckpicker.png`, `f6-ondevice-logcat.txt`, `f6-fork-rpc-symbols.txt` | `3189d4336`      |
| F7  | Android mobile CFA experience — bundled decks auto-import, ethics card multi-span on device             | `cfa-f7-test` + on-device (adb)               | 3 pass · 8 device screenshots | `f7-ondevice-*.png`, `f7-ondevice-autoimport-logcat.txt`                          | `126a29823`      |
| F8  | Cross-platform persistence — deck/ethics/exam-config/queue all reach a fresh phone over sync            | `cfa-f8-test`                                 | 3 pass                        | `f8-persistence-report.txt`, `f8-persistence.log`, `docs/cfa/PLATFORM-MATRIX.md`  | `3b74faf9e`      |
| F9  | Final gate — full suite, real numbers, reachability, this checklist                                     | `tools/cfa/f9_reachability.py`                | REACHABILITY: PASS            | `f9-full-suite.log`, `f9-reachability.txt`                                        | _this iteration_ |

## End-to-end reachability (F9)

A fresh collection seeded via the first-launch seeder exposes every feature.
Verified headlessly (`proof/gnhf2/f9-reachability.txt`):

```
F0b seed          : main_seeded=True ethics_seeded=True +630 notes +30 ethics config_set=True
F0b exam config   : {'exam_date': '2026-08-25'}
F0a llm_client    : ai_enabled=False ok=False error=no_api_key      (AI-off contract holds)
F1 grader         : passages=30 spans=73 perfect_attempt_correct=True
F2 semantic grade : source=fallback correct=True                    (AI-off falls back to F1)
F3 tab-fill AIoff : ok=False (AI off -> no draft, back untouched)
F4 readiness      : call=likely fail p_pass=0.07 acc=0.50 CI=[0.30,0.70]  (numeric, no give-up wall)
F5 design tokens  : primary=#0f4c81 keys=22
F6/F7/F8 engine   : build_exam_queue -> 5 cards (shared Rust engine)
F9 REACHABILITY: PASS
```

To launch the real desktop app into a freshly-seeded CFA profile:

```bash
ANKI_BASE=/tmp/cfaFinal/ankibase just run
```

## Gate: no-mistakes unavailable → documented fallback

`no-mistakes` is available on this machine and its push target _is_
`github.com/adarshrajesh-ui/ankiCFA`, **but** its pipeline requires
self-commits / push / PR / merge, which the gnhf iteration rules forbid (the
orchestrator owns commits and the merge to `origin/main`). Per the objective's
explicit fallback clause, each feature was therefore validated through the
**manual gate**: the feature's full relevant test suite green + rendered /
adb-screencap proof. This is recorded per-iteration in
`.gnhf/runs/objective-ship-a-pro-687de8/notes.md`.

## Honest caveats

- **AI-off is the default and fully functional.** With no `OPENAI_API_KEY`, F0a
  returns `{ok:False}`, F2 semantic grading falls back to the deterministic F1
  grader, F3 tab-fill is disabled with a tooltip, and the eval's LLM ≥0.80
  assertion is _skipped_ (never faked). The entire test suite passes AI-off.
- **Scoring is not validated against real exam data.** F4 readiness (SM-2
  recall fallback + Bayesian 95% credible band + pass/fail call vs the ~65% MPS
  proxy) carries a standing _"not validated against real exam data"_ label; the
  eval harness is a seeded synthetic-learner simulation, likewise labelled.
- **Mobile is shared-engine + synced-content, not a full port.** On Android the
  fork **Rust engine** (BuildExamQueue / DeadlineRetention) runs on-device and
  the **decks / note-types / ethics cards / exam config** reach the phone via
  bundled `.apkg` (content) + AnkiWeb sync (col.conf). **Desktop-only:** the AI
  tab-fill editor button, LLM ethics grading UI, and the Exam Readiness scoring
  dialog. Full split: `docs/cfa/PLATFORM-MATRIX.md`.
- **All 660 authored items are original.** No copyrighted CFA Institute content;
  the leakage check confirms no held-out eval question overlaps a training front.

## Merge status

Features F0a–F8 are committed on branch
`gnhf/objective-ship-a-pro-687de8` at the SHAs above; F9 is this iteration. The
gnhf orchestrator performs the commit and the merge to `origin/main` — the SHAs
above are the per-feature checkpoints on the run branch.
