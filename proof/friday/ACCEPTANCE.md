# ankiCFA — Acceptance D1–D7 — FULLY EVIDENCED ✅

ankiCFA is now a **native CFA Level II prep product**: desktop boots to a CFA
Home, the app is branded ankiCFA on desktop **and** mobile, the honest scores
come from **one shared Rust engine** (`ComputeCfaScores`) that both platforms
call, ethics is the minimal-pairs flagship, sync round-trips real reviews, and
every AI feature is off-by-default with a deterministic fallback and named
provenance.

All 6 workstreams are merged to `main` (`origin/main` @ `a3e982b7d`); the full
`just check` is green; every acceptance item below points to a runnable check or
an evidence file under `proof/friday/`.

## Terminal criteria

| DONE criterion                             | Status | Evidence                                                                                                                                                                                       |
| ------------------------------------------ | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Build green** (full `just check`)        | ✅     | `hygiene/final-justcheck-exit0.txt` → "All checks passed! Build succeeded". Cross-checked: `cargo test -p anki` = 544 pass; CFA python 49 pass (`phase0/integration-verification.txt`).        |
| **All 6 branches merged**                  | ✅     | `origin/main` contains `friday/{ethics,sync,desktop-shell,hygiene}` + the phase0 spine + `friday/mobile`, merged in order Phase0→W3→W5→W1→W6 (`git merge-base --is-ancestor` passes for each). |
| **Sync recording exists**                  | ✅     | `sync/roundtrip.mp4`, `sync/roundtrip-take1-phone-reviews.mp4`, `sync/offline-then-sync.mp4` + `sync/inc2-desktop-after-phone-reviews.txt` (revlog delta).                                     |
| **Eval gate passes**                       | ✅     | `phase0/eval-gate-PASS-ai-on-gpt4o.txt` → GPT-4o LLM grader, 30 attempts, **agreement 0.833 ≥ 0.80 → PASS**. AI-off baseline 0.733 (`phase0/eval-baseline-ai-off.txt`).                        |
| **Desktop reads as native CFA + 3 scores** | ✅     | `desktop-shell/item2-home-after.png` (CFA Home), `item1-branding-*` (ankiCFA branding), `item3-toolbar-menu-*`. Scores via the RPC (`phase0/parity-rpc-vs-cfapy.txt`).                         |
| **Mobile reads as native CFA + 3 scores**  | ✅     | `phase0/mobile-09-readiness.png` (Readiness/Memory/Performance + give-up + 8 topics), `phase0/mobile-02/03/06` (ankiCFA branding, Ethics minimal-pairs). See `phase0/MOBILE-VERIFICATION.md`.  |
| **ACCEPTANCE.md fully evidenced**          | ✅     | this file.                                                                                                                                                                                     |

## D1–D7 + parity

| #                           | Requirement                                                         | Status | Evidence                                                                                                                                                         |
| --------------------------- | ------------------------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Parity**                  | desktop == mobile == old Python                                     | ✅     | `phase0/parity-rpc-vs-cfapy.txt` — RPC == `cfa.py` field-by-field to **1e-9**; permanent gate `just cfa-parity-test`. Mobile calls the same engine.              |
| **D1**                      | AI names a source                                                   | ✅     | `ethics/item5-emitted-payload.json` — `{source, standard:"II(A)…", item_id:"SMD-01", model, rationale}`. Schema: `docs/cfa/AI-PROVENANCE.md`.                    |
| **D2**                      | eval-before-serve, accuracy + wrong-answer-rate vs baseline at 0.80 | ✅     | `phase0/eval-gate-PASS-ai-on-gpt4o.txt` — 0.833 ≥ 0.80 PASS (confusion matrix → wrong-answer-rate); AI-off baseline 0.733.                                       |
| **D3**                      | deterministic score AI-off + in-app toggle                          | ✅     | scores are AI-free (parity gate is exact AI-off); toggle: `just cfa-ai-toggle-test` (7 tests) + `desktop-shell/item5-ai-settings-{off,on}.png`.                  |
| **D4**                      | REAL two-way sync round-trip, recorded, no double-count             | ✅     | `sync/roundtrip*.mp4` (phone→sync→desktop and reverse) + revlog deltas; no-double-count **tested** (`just cfa-parity-test`, rust `double_count_fix_*`).          |
| **D5**                      | offline-then-sync                                                   | ✅     | `sync/offline-then-sync.mp4` + `sync/inc4-offline-delta.txt`, `inc4-desktop-full-download.txt`.                                                                  |
| **D6**                      | phone shows 3 scores w/ ranges + give-up                            | ✅     | `phase0/mobile-09-readiness.png` — 3 scores, give-up thresholds match `cfa.py` byte-for-byte (200/50%/30), 8 canonical topics.                                   |
| **D7**                      | eval numbers + phone→desktop recording                              | ✅     | eval numbers `phase0/eval-gate-PASS-ai-on-gpt4o.txt` + recording `sync/roundtrip-take1-phone-reviews.mp4`.                                                       |
| **Fresh-seed reachability** | desktop AND mobile                                                  | ✅     | desktop `just cfa-f9-gate`; mobile app ships seeded CFA decks (Ethics Pairs + CFA Level II), reachable from a fresh profile (`phase0/mobile-02-deckpicker.png`). |

## How to re-run (AI-off unless noted)

`just cfa-parity-test` · `just cfa-ai-toggle-test` · `just cfa-scores-test` ·
`just cfa-f4-test` · `just cfa-types-test` · `just cfa-eval` · `just cfa-f9-gate` ·
`cargo test -p anki` · full: `just check`. Eval **gate** (D2, AI-on GPT-4o):
`just cfa-ethics-eval` with `OPENAI_API_KEY` set (key never committed).
