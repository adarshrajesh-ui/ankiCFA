# Phase-0 Spine — Report

**Delivered & pushed** (`friday/phase0`, off `origin/main`, isolated worktree so
the contended shared tree was never touched).

The core win: the honest CFA scores now come from **one read-only Rust engine**,
`ComputeCfaScores`, that desktop and the AnkiDroid client both call — computed in
exactly one place, so desktop == mobile == old Python. It is a faithful f64 port
of `pylib/anki/cfa.py` (Memory / Performance / Readiness + the Bayesian hero
band) using the *same* SQL and math, so parity holds by construction:
`just cfa-parity-test` shows the RPC equals the Python reference **field-by-field
to 1e-9**. Added the requested **double-count fix** — graded reviews counted at
most once per (card, day), so an offline dual-device round-trip can't inflate the
evidence (tested). `cfa.py` is now a thin wrapper over the RPC (pure-Python kept
as `_py_*` reference/fallback); its dataclass API is unchanged, so workers and UI
are unaffected. Read-only throughout — 9 sync tests confirm sync/FSRS/undo intact.

Also shipped: the **AI toggle** (3 `col.conf` keys, `key AND master AND feature`,
default OFF, deterministic scores AI-off), the **sync harness**
(`just cfa-syncserver` + `SYNC-SETUP.md`), and the contract docs
(`NATIVE-CFA-SPEC.md` with Home/branding/merge-rules, `AI-PROVENANCE.md`).
Tests: 3 Rust `cfa_scores` + 150 scheduler + 54 pylib/toggle + 9 sync, all green.

**Not done this session (honestly gated):** the worker branches W1–W6 aren't
pushed yet, so there is nothing to merge for Phase-2. D4/D5/D6/D7 need the mobile
AAR rebuilt from merged `main` + a running emulator. `ACCEPTANCE.md` records every
D-item's status and the exact unblock steps. Phase-0 unblocks W1 (Home) and W4
(mobile scores) — merge it first.
