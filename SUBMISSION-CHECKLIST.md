# CFA Exam-Prep — Submission Checklist

All 10 features are implemented, each with a passing test suite and a
screenshot/log as proof. Every change was made **additively** on top of
baseline `main` (`d5867e5b5`) so Anki's upstream behaviour is preserved and no
copyrighted CFA Institute content is used — only original authored items.

Run the whole gate from a clean checkout with:

```
just cfa-deck-validate && just cfa-eval-leakage      # stdlib validators
just cfa-deck-test cfa-test cfa-menu-test \
     cfa-seed-test cfa-scores-test cfa-types-test \
     cfa-eval-test cfa-sync-test                     # 94 py/qt tests
cargo test -p anki --lib cfa_deadline                # 10 rust tests
cargo test -p anki --lib exam                        # 15 rust tests
```

## Feature status

| # | Feature | Test suite (recipe) | Result | Proof file | Commit SHA |
|---|---------|--------------------|--------|-----------|-----------|
| 1 | CFA Level II deck (630 items, `los::` tags) + JSONL validator | `just cfa-deck-test` / `cfa-deck-validate` | 7 pass · 630 items valid | `proof/gnhf/feature1-cfa-deck.png` | `63e06be62` |
| 2 | Deadline-retention DOK-4 (read-only RPC) + Python e2e | `just cfa-deadline` · `cargo test cfa_deadline` | 7 py + 10 rust pass | `proof/gnhf/feature2-deadline.png` | `3ba6c0f40` |
| 3 | Ethics tap-to-highlight grading (correct/somewhat/wrong) | `just cfa-test` + e2e | 43 pass (incl. Py↔JS) | `proof/gnhf/feature3-ethics-highlight.png` | `667f2d4dc` |
| 4 | Desktop CFA menu — 4 study actions | `just cfa-menu-test` | 3 pass (asserts 4 actions) | `proof/gnhf/feature4-cfa-menu.png` | `b13afba4e` |
| 5 | First-launch idempotent seeder (both decks + config) | `just cfa-seed-test` | 3 pass | `proof/gnhf/feature5-first-launch.png` | `7266a4b72` |
| 6 | Three honest scores (Memory/Performance/Readiness), ranges + give-up | `just cfa-scores-test` | 10 pass | `proof/gnhf/feature6-scores.png` | `a52e5e628` |
| 7 | Held-out eval harness (30×2 paraphrase) + leakage check | `just cfa-eval-test` / `cfa-eval-leakage` | 6 pass · leakage clean | `proof/gnhf/feature7-eval.png` | `eeb155f34` |
| 8 | Content-type-aware weighting in BuildExamQueue | `just cfa-types-test` · `cargo test exam` | py + 15 rust pass | `proof/gnhf/feature8-content-type.png` | `9b02f07ae` |
| 9 | Two-way sync + more-recent-wins conflict rule | `just cfa-sync-test` / `cfa-sync` | 6 pass (round-trip) | `proof/gnhf/feature9-two-way-sync.png` | `1384f1ddc` |
| 10 | Final consolidation — full suite + reachability + this checklist | this file | 94 py/qt + 25 rust green | `proof/gnhf/feature10-final.png` | _this iteration_ |

## End-to-end reachability

A fresh profile seeded at `ANKI_BASE=/tmp/cfaFinal/ankibase` (via the
first-launch seeder) exposes every feature. Verified headlessly:

```
SEED: main_seeded=True ethics_seeded=True notes_added=630 ethics_added=30 config_set=True
CFA Level II cards: 630        CFA::Ethics Pairs cards: 30
Feat 4/8 build_exam_queue -> 5 cards; type-mult wired: True
Feat 2 deadline_retention -> read-only, undo-preserving
Feat 6 memory/performance/readiness -> honest ranges, abstain when no reviews (give-up rule)
Feat 4 menu -> setup_menu builds exactly 4 actions
```

To launch the real desktop app into a freshly-seeded CFA profile:

```
ANKI_BASE=/tmp/cfaFinal/ankibase just run
```

The **CFA** menu then offers: Exam Readiness · Study Ethics Minimal-Pairs ·
Study by Exam Priority · Peak-on-Exam-Day.

## Honesty notes

- No bare scores: Memory, Performance and Readiness are all reported as
  ranges with an explicit give-up (abstain) rule when data is insufficient.
- Readiness carries a standing **"not validated against real exam data"**
  label; the eval harness is a seeded synthetic-learner simulation, likewise
  labelled.
- All 660 authored items are original; the leakage check confirms no held-out
  eval question overlaps a training deck front (Jaccard < 0.6).

## Merge status

Features 1–9 are committed on branch `gnhf/resuming-after-a-cra-9d3f67` at the
SHAs above; Feature 10 is this iteration. The gnhf orchestrator performs the
commit and the merge to `origin/main` at consolidation — the SHAs above are the
per-feature checkpoints on the run branch.
