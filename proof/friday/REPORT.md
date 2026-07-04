# ankiCFA — Final Report

ankiCFA is a **native CFA Level II prep product**, not "Anki + a tab." Desktop
boots to a CFA Home; both platforms are branded ankiCFA; the three honest scores
(Memory / Performance / Readiness) + the Bayesian band come from **one shared
Rust engine**, `ComputeCfaScores`, that desktop (`anki.cfa`) and AnkiDroid
(`col.backend.computeCfaScores`) both call — so **desktop == mobile == old
Python**, verified field-by-field to 1e-9. Ethics is the minimal-pairs flagship
(one-passage retired); AI is off by default with a deterministic fallback and
named provenance.

**Phase 0 (spine, mine).** ComputeCfaScores RPC in proto + rslib, a faithful
f64 port of `cfa.py` with the **(card,day) double-count fix**; `cfa.py` is now a
thin wrapper; AI toggle (3 `col.conf` keys, key AND master AND feature); the
`cfa-syncserver` harness; and the contract docs. On `main`.

**Phase 2 (integration + verification).** All six workstreams merged to `main`
in order (Phase0→ethics→sync→desktop-shell→hygiene, + mobile); full `just check`
green. I verified the integrated tree end-to-end (544 rust, 49 CFA python incl.
the parity gate) and ran the **eval gate AI-on with GPT-4o: agreement 0.833 ≥
0.80 → PASS**. I drove the emulator to capture D6 (phone shows the 3 scores +
give-up, thresholds matching the engine). Sync worker's recordings prove D4/D5.

**Acceptance:** D1–D7 fully evidenced in `ACCEPTANCE.md`, each mapped to a
runnable check or a file under `proof/friday/`. Rules held: additive,
sync/FSRS/undo intact, key never committed, GPT-4o, desktop↔mobile parity.
