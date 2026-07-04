# Phase-0 Spine — NOTES

Branch: `friday/phase0` (off `origin/main` @ `6ef32ec8c`), built in an isolated
worktree so it never touched the contended shared tree (other tabs were live,
the shared `cargo check` was transiently red, and the branch was switched under
the session).

Owner scope: the shared spine the worker tabs build on. **Additive only**;
FSRS/sync/undo untouched.

## Delivered

1. **`ComputeCfaScores` RPC** — `proto/anki/scheduler.proto` + new
   `rslib/src/scheduler/cfa_scores.rs`, a faithful Rust port of
   `pylib/anki/cfa.py` (Memory weighted FSRS-R ± pstdev; Performance
   first-exposure Wilson95; Readiness logistic P(pass); Bayesian hero band).
   All numeric fields are `double` (f64) for exact parity. Uses the same SQL
   (`extract_fsrs_retrievability`) + f64 math as Python, so parity is by
   construction. `libm::erf` matches Python `math.erf` for the Bayesian
   `norm_cdf`.
   - **Double-count fix:** graded reviews counted at most once per (card, day).
   - 3 Rust unit tests (`cargo test -p anki --lib cfa_scores`): abstain path,
     happy path (all 4 scores), double-count dedup. + 150 scheduler tests green.

2. **`pylib/anki/cfa.py` thin wrapper** — the 4 public functions delegate to the
   RPC (`col._backend.compute_cfa_scores`); pure-Python impls kept as `_py_*`
   (reference + fallback for an older backend). Existing dataclass API unchanged
   → callers/workers unaffected.

3. **Parity proof** — `pylib/tests/test_cfa_parity.py` (`just cfa-parity-test`):
   RPC == `_py_*` field-by-field to **1e-9**; double-count fix asserted. Ran
   end-to-end through a rebuilt `_rsbridge.so` (see parity-rpc-vs-cfapy.txt).
   54 pylib/toggle CFA tests green via the RPC path (2 same-day-packed fixtures
   updated to realistic day-spacing).

4. **AI toggle** — `cfa/ai/llm_client.py`: `col.conf` keys `cfa_ai_enabled`
   (master, default off) + `cfa_ai_grading_enabled` + `cfa_ai_tabfill_enabled`;
   `ai_feature_enabled(f) = key AND master AND feature`. 7 tests
   (`just cfa-ai-toggle-test`). Deterministic AI-off by default.

5. **Sync harness** — `tools/cfa/syncserver.py` + `just cfa-syncserver`:
   long-running fixed-credential LAN server; `docs/cfa/SYNC-SETUP.md`.

6. **Contracts** — `docs/cfa/NATIVE-CFA-SPEC.md` (Home dashboard, branding,
   ethics=minimal-pairs, RPC interface, **merge rules**),
   `docs/cfa/AI-PROVENANCE.md` (`{source,standard,item_id,model,rationale}` +
   toggle).

## Mobile (integration step, not in this branch)

The `col.backend.computeCfaScores` binding is auto-generated when the AAR is
rebuilt from merged `main` (`Anki-Android-Backend/cfa_build_fork_engine.sh`).
The seam `CfaScoresProvider.scores(col)` already exists (`rpcAvailable()` +
`SOURCE_RPC`). Wire the typed call + map to `CfaScores` after Phase-0 merges,
then `bash scripts/verify_mobile.sh`. That is **D6**.

## Build notes / how to reproduce

- Rust: `cargo test -p anki` (seed the fresh worktree's `ftl/core-repo` +
  `ftl/qt-repo` from a built checkout; copy `out/extracted/protoc`). The proto
  `build.rs` regenerates `descriptors.bin` + `_backend_generated.py` itself.
- `.so`: `cargo build -p rsbridge --features native-tls` (plain `cargo check -p
  anki` is a red herring — the tokio `io-util` methods are only enabled under a
  tls feature / the test profile).
- Full `just check` (mypy/ruff/ts/full suite) runs at integration; changed
  Python is ruff-clean here.

## Merge

Merge order per NATIVE-CFA-SPEC §6: **Phase0 → W2 → W3 → W1/W4/W5/W6**. Rebase
before merge; keep `just check` green; CFA suites pass AI-off (`.env` aside).
