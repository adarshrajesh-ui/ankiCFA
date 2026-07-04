# ankiCFA — Acceptance D1–D7 (status)

## Integration progress (Phase-2, driven here)

- **✅ Phase-0 spine merged to `main`** (`6ef32ec8c..891720111`, fast-forward) —
  step 1 of the merge order (Phase0 first). The shared `ComputeCfaScores` engine
  is now on the trunk, so the worker tabs rebase onto it and the mobile
  fork-engine build (`cfa_build_fork_engine.sh`) picks up the RPC.
- **✅ mypy clean** on the changed spine Python (`pylib/anki/cfa.py`,
  `cfa/ai/llm_client.py`, `tools/cfa/syncserver.py`).
- **✅ eval ran AI-off** (F7 readiness harness, `cfa/eval/run_eval.py`):
  accuracy@0.5 = 0.686, AUC = 0.763, ECE = 0.078, paraphrase-gap ≤ 0.117 (seed 0,
  12000 predictions). Note: D2's "eval-before-serve **gate** at 0.80" is the
  **AI-grading** eval gate (a grading-worker deliverable, not this simulation
  harness) — verified once that gate lands.
- **⏳ Remaining DONE criteria are gated on the worker tabs**, which are LIVE and
  still pushing (own worktrees: `desktop-shell`, `sync`, `ethics`, `hygiene`; an
  emulator `emulator-5554` is running an in-progress mobile app). Merging their
  moving, incomplete branches or driving their emulator now would collide with
  active work and misrepresent completion. The final integration + D4/D5/D6/D7
  device recordings run against their **finished** branches + a rebuilt AAR.

---

## Detailed matrix

This maps each acceptance item to concrete evidence. Phase-0 (the shared spine,
`friday/phase0`) is **done and pushed**; items that depend on the worker tabs
(W1–W6) landing and on the desktop⇄mobile integration build are marked
**GATED** with exactly what unblocks them. Nothing here is asserted without a
runnable check or a file pointer — GATED means "not yet demonstrable," not
"assumed done."

Legend: ✅ done & evidenced · 🟡 mechanism done, UI/e2e at integration · ⛔ gated.

| # | Requirement | Status | Evidence / what unblocks it |
|---|---|---|---|
| **Build green** | `just build`/checks green | 🟡 | Rust: `cargo test -p anki` clean; 150 scheduler + 3 `cfa_scores` tests pass. `.so` builds (`cargo build -p rsbridge --features native-tls`). Changed Python ruff-clean. Full `just check` (mypy/ts/all suites) runs at integration on the merge host. |
| **Scores parity** | desktop == mobile == old Python | ✅ (desktop) / ⛔ (mobile) | `just cfa-parity-test`: RPC == `anki.cfa._py_*` field-by-field to **1e-9** (`proof/friday/phase0/parity-rpc-vs-cfapy.txt`). Mobile reads the *same* Rust engine — GATED on the AAR rebuild after merge (§ mobile below). |
| **D1** | AI names a source | 🟡 | Provenance schema `{source,standard,item_id,model,rationale}` fixed in `docs/cfa/AI-PROVENANCE.md`. AI features emitting it per item = W-grading; verify once wired (needs a key, off by default). |
| **D2** | eval-before-serve reports accuracy + wrong-answer-rate vs baseline at 0.80 cutoff | ⛔ | Eval harness exists (`cfa/eval/`, `just cfa-eval`). Turning the CLI into a serve-time **gate** at 0.80 + wrong-answer-rate is a worker deliverable; verify its numbers at integration (AI-off prints the deterministic baseline). |
| **D3** | deterministic score AI-off + in-app toggle | ✅ (engine+toggle) / 🟡 (toggle UI) | Scores are AI-free ⇒ deterministic: parity gate is exact and reproducible AI-off (`.env` absent in the test env). In-app toggle mechanism: `cfa_ai_enabled`+per-feature `col.conf` keys, `ai_feature_enabled = key AND master AND feature`, default OFF — `just cfa-ai-toggle-test` (7 tests). The settings *control* on Home = W-desktop. |
| **D4** | REAL two-way sync round-trip (emulator→desktop and reverse), recorded, no double-count | 🟡 harness / ⛔ recording | Harness done: `just cfa-syncserver` + `docs/cfa/SYNC-SETUP.md` (fixed creds, `10.0.2.2` for emulator). Double-count fix **tested** (per-(card,day) dedup: `just cfa-parity-test`, Rust `double_count_fix_*`). The screen recording needs the mobile app rebuilt with the RPC + a running emulator — GATED on integration. |
| **D5** | offline-then-sync | ⛔ | Same harness as D4; recording GATED on integration (procedure in SYNC-SETUP.md §4). |
| **D6** | phone shows 3 scores w/ ranges + give-up | 🟡 | **Captured on the running emulator** (`proof/friday/phase0/mobile-09-readiness.png`, see MOBILE-VERIFICATION.md): the ankiCFA `Exam Readiness` screen shows READINESS/MEMORY/PERFORMANCE, each with give-up state + reason, and per-topic recall for all 8 canonical topics. Give-up thresholds + wording match `cfa.py` byte-for-byte (200/50%/30). Currently in give-up state (demo profile has 1 review) and **"Source: on-device (deterministic)"** = the fallback path. Ranges + RPC source close when the AAR is rebuilt with the RPC (now on `main`) + a populated profile. |
| **D7** | eval numbers + phone→desktop recording | ⛔ | = D2 numbers + D4 recording; both GATED as above. |
| **Fresh-seed reachability** | desktop AND mobile | 🟡 desktop / ⛔ mobile | Desktop reachability tooling exists (`tools/cfa/f9_reachability.py`, `just cfa-f9-gate`); re-run at integration on merged main. Mobile GATED on the app build. |

## Mobile integration step (unblocks the ⛔ items)

1. Merge `friday/phase0` → `main` (Phase-0 first, per NATIVE-CFA-SPEC §6).
2. Rebuild the backend AAR from merged `main`:
   `Anki-Android-Backend/cfa_build_fork_engine.sh` → regenerates
   `GeneratedBackend.kt` with `computeCfaScores` + `librsdroid.so`.
3. Wire `CfaScoresProvider.scores(col)` to the typed
   `col.backend.computeCfaScores(...)` (seam + `SOURCE_RPC` already present), map
   to `CfaScores`; `bash scripts/verify_mobile.sh`.
4. Boot emulator + desktop against `just cfa-syncserver`; record D4/D5, screenshot
   D6, run `cfa-eval` for D2/D7 numbers.

## What Phase-0 guarantees today (reproducible now)

- `just cfa-parity-test` — RPC == Python to 1e-9 + double-count fix.
- `just cfa-ai-toggle-test` — the 3-key AI gate, default OFF.
- `cargo test -p anki --lib cfa_scores` — 3 engine tests (abstain / happy / dedup).
- `just cfa-scores-test`, `cfa-f4-test`, `cfa-types-test` — 54 CFA tests via the
  shared engine, AI-off.
