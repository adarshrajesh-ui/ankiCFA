# Wednesday Submission Proof — Checklist

Maps every Wednesday submission **gate line** → **proof artifact (path)** →
**status**. Assembled by a 10-agent fleet, then reconciled in a final
coordinator pass after all agents completed. The only remaining `pending-<fleet>`
items are two screen recordings that are physically blocked on other fleets.

- **Baseline:** `main` HEAD `b431cb1265f81abe8e18eff9c8839f3a25aae665` (`b431cb126`).
- **Work branch:** `chore/wed-proof` (branched off `main` at the baseline; the
  other fleets' uncommitted `v3.py`/`mod.rs` edits are preserved in the tree).
- **Platform recorded:** Darwin arm64, Python 3.14.2 (arm64), Rust 1.92.0.
- **Gate sources read:** `proof/GATE.md` (day-one build/run gate),
  `proof/README.md` (proof-artifact index), `README.md`, `docs/prd/PRD.md`.

## Status legend

| Token                     | Meaning                                                    |
| ------------------------- | ---------------------------------------------------------- |
| `DONE`                    | Artifact exists at the path and is non-trivial / verified. |
| `DONE*`                   | Present & verified, with a documented caveat (see Notes).  |
| `pending-installer-fleet` | Blocked on the installer fleet's deliverable.              |
| `pending-ankidroid-fleet` | Blocked on the AnkiDroid (mobile) fleet's deliverable.     |
| `owned: packaging fleet`  | Reference to another fleet's artifact (present).           |

## Gate → artifact → status

| #  | Gate line                                                                         | Proof artifact (path)                                                               | Status                    | Notes                                                                                                                                                                                                                                                                                                                                                |
| -- | --------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | Clean-BUILD screen recording                                                      | `demo/build.mp4`                                                                    | `DONE`                    | Present (~9.5 MB, 75s timelapse, h264, full-decode verified). Shows a genuine **from-scratch** `just build` after `just clean`: 713 `Compiling …` lines, all **62/62** ninja steps, `Build succeeded in 256.41s`, zero "no work to do". (Replaced the initial incremental-no-op capture.) Corroborated by `proof/build-baseline.log`.                |
| 2  | Clean-MACHINE install screen recording                                            | `demo/install.mp4`                                                                  | `pending-installer-fleet` | Recording of the wheels install on a fresh machine. Log proof exists (`proof/clean-machine-install.log`); the **video** is owned by the installer fleet and must be captured after it lands the packaged bundle.                                                                                                                                     |
| 3  | Phone review-session screen recording                                             | `demo/phone-review.mp4`                                                             | `pending-ankidroid-fleet` | AnkiDroid review loop on device/emulator. Must be captured after the AnkiDroid fleet produces a runnable mobile build.                                                                                                                                                                                                                               |
| 4  | Desktop reviewer-session recording                                                | `demo/desktop-review.mp4`                                                           | `DONE`                    | Present (~3.0 MB, 45s, h264, decode-verified). Shows a real review flow (reveal + grade on 3 CFA `los::`-tagged cards) then the native **CFA → Exam Readiness** dialog: overall recall **87%–92% (mid 90%)**, **100% coverage (10/10 topics)**, 543 graded reviews, per-topic recall **ranges**. Closes the audit's "no desktop reviewer frame" gap. |
| 5  | Commit-hash consistency (`.commit` + BASELINE re-pinned to main HEAD `b431cb126`) | `proof/.commit`, `proof/BASELINE.md`                                                | `DONE`                    | `.commit` = `b431cb1265f81abe8e18eff9c8839f3a25aae665`; `BASELINE.md`/`GATE.md`/`proof/README.md` re-pinned off the orphan `9cc8f39` and stale `6770ad3`/`cfa/exam-queue-mvp`.                                                                                                                                                                       |
| 6  | Interpreter arch/version recorded in install/baseline proof                       | `proof/BASELINE.md`                                                                 | `DONE`                    | Records **Python interpreter 3.14.2 (arm64)**, Darwin arm64, cargo/rustc 1.92.0, node v22.17.0, protoc 3.20.3.                                                                                                                                                                                                                                       |
| 7  | Rust tests at HEAD                                                                | `proof/rust-tests.log`                                                              | `DONE`                    | `test result: ok. 8 passed; 0 failed; 0 ignored` — the `BuildExamQueue` exam-queue tests, now **8** (the uncommitted `mod.rs` edits add `exam_queue_includes_new_cards` + `exam_queue_mixes_new_and_due_cards`).                                                                                                                                     |
| 8  | Python tests at HEAD                                                              | `proof/python-tests.log`                                                            | `DONE`                    | Full `just test-py`: **CFA `test_cfa.py` 7/7 PASSED** (verified twice). Aggregate 203 passed, **2 failed**. The 2 failures are the pre-existing offline **Briefcase installer** tests (`qt/tests/test_installer.py`) — environmental, unrelated to CFA, and stock/unmodified (matches `proof/worktree-check.log`).                                   |
| 9  | Build logs at HEAD                                                                | `proof/build-baseline.log`, `proof/build-after-changes.log`                         | `DONE`                    | Both green: baseline `Build succeeded in 531.30s` (recompiled the `anki` crate from the uncommitted edit; long due to 10-agent + cross-fleet contention), after-changes `Build succeeded in 2.39s` (incremental).                                                                                                                                    |
| 10 | README (exam up front, AGPL+Anki credit, both apps' build, architecture)          | `README.md`                                                                         | `DONE`                    | Covers all four: exam (CFA L2) up front; AGPL-3.0-or-later + Anki credit; **both apps' build** ("Desktop (this repo)" + "Mobile (AnkiDroid fork)"); "Architecture overview" layer diagram.                                                                                                                                                           |
| 11 | One-page Rust-change note                                                         | `docs/cfa/RUST_ENGINE_NOTE.md`                                                      | `DONE`                    | Why `BuildExamQueue` lives in Rust + merge-difficulty analysis. Verified against real diffs; corrected for the working-tree edits (queue now covers **due + new** cards; **8** unit tests). Its "upstream files touched" table is intentionally **engine-scoped (3 files)**.                                                                         |
| 12 | Upstream files-touched list                                                       | `docs/cfa/UPSTREAM_FILES.md`                                                        | `DONE`                    | Git-derived **comprehensive** list: **7** modified upstream files (the 3 engine files + `qt/aqt/main.py`, `justfile`, `CONTRIBUTORS`, `README.md`) + new fork-only files; generated code excluded. Complements #11 (engine-scoped) — the differing counts are scope, not contradiction.                                                              |
| 13 | Demo video script (3–5 min)                                                       | `docs/cfa/DEMO_SCRIPT.md`                                                           | `DONE`                    | ~4:30, 5 segments + close, each mapped to a backing artifact; flags the pending phone clip.                                                                                                                                                                                                                                                          |
| 14 | Packaging doc                                                                     | `docs/cfa/PACKAGING.md`                                                             | `owned: packaging fleet`  | Present (reference, not edited by this fleet).                                                                                                                                                                                                                                                                                                       |
| 15 | Wheels / clean-machine install proof logs                                         | `proof/wheels.log`, `proof/clean-machine-install.log`                               | `DONE`                    | Wheels built (`anki-26.5`, `aqt-26.5`); fresh venv install imports `anki`/`aqt`/`anki.cfa`/`aqt.cfa` → "CLEAN-MACHINE INSTALL OK". The **recording** (b) is `demo/install.mp4` = `pending-installer-fleet`.                                                                                                                                          |
| 16 | Perf guardrail, clippy, complexity, full `just check`                             | `proof/perf-50k.log`, `proof/clippy.log`, `proof/complexity.log`, `proof/check.log` | `DONE`                    | Perf: 50k due cards, `build_exam_queue` best-of-5 ≈ 337 ms. Clippy clean. Complexity: no `cfa.py` function > 20. `proof/worktree-check.log` is the authoritative clean-worktree run — only remaining failures are the environmental Briefcase installer tests (stock/unmodified).                                                                    |

## Summary counts (final coordinator pass — all 10 fleet agents complete)

- **DONE:** 13 gate lines — #1, #4, #5, #6, #7, #8, #9, #10, #11, #12, #13, #15, #16.
- **Reference (owned elsewhere, present):** 1 — #14 `docs/cfa/PACKAGING.md`.
- **Pending other fleets (recordings only):** 2 — #2 `demo/install.mp4` (`pending-installer-fleet`), #3 `demo/phone-review.mp4` (`pending-ankidroid-fleet`).

## What's left / next actions

All text/doc proof, both test suites, the build logs, the commit/baseline
re-pin, and **two of the three required recordings** (clean-build + desktop
reviewer) are in place. What remains:

1. **`demo/install.mp4` — `pending-installer-fleet`.** Capture the clean-machine
   wheels install _after_ the installer fleet finalizes the packaged bundle
   (`dist/launch-ankiCFA.sh` + wheels). Log proof already exists
   (`proof/clean-machine-install.log`); record the interpreter arch/version on
   camera so the install is meaningful.
2. **`demo/phone-review.mp4` — `pending-ankidroid-fleet`.** Record a phone
   review session _after_ the AnkiDroid fleet produces a runnable mobile build
   (a card synced/loaded and reviewed on device/emulator).
3. **(Done) `demo/build.mp4` from-scratch re-record** — replaced the incremental
   no-op capture with a genuine from-scratch `just build` (256.41s, 713 compiles,
   62/62 steps) rendered as a 75s timelapse.

**Blocking order:** items (1) and (2) cannot be recorded now — they must wait
for the installer and AnkiDroid fleets to land their deliverables. Nothing else
blocks the submission from this fleet's side.

## Verification log

Existence + content were checked repeatedly during assembly and once more in the
final coordinator pass after all agents completed.

- **22:35–22:42 CDT (assembly, agent monitoring):** `demo/` empty; docs landing
  incrementally; `proof/{rust-tests,python-tests,build-baseline}.log` observed
  header-only and byte-frozen — later understood to be the four non-holder build
  agents **waiting behind the shared `/tmp/ankicfa_build.lock`** (serialized so
  concurrent builds could not clobber `out/`/`target/`), not a stall.
- **~23:26 CDT (final coordinator pass, all 10 agents done):**
  - `demo/build.mp4` (1,111,996 B) and `demo/desktop-review.mp4` (3,120,414 B) present & decode-verified.
  - `proof/rust-tests.log` → `8 passed; 0 failed`. `proof/python-tests.log` → CFA `7 passed`; aggregate `203 passed, 2 failed` (Briefcase installer, environmental).
  - `proof/build-baseline.log` → `Build succeeded in 531.30s`; `proof/build-after-changes.log` → `Build succeeded in 2.39s`.
  - `proof/.commit` = `b431cb126`; protected edits `pylib/anki/scheduler/v3.py` & `rslib/src/scheduler/service/mod.rs` still present (`M`), untouched; `docs/cfa/PACKAGING.md` unmodified.
  - Orphaned build lock cleared; the from-scratch `demo/build.mp4` re-record **completed** — replaced with a genuine full-compile timelapse (9.5 MB; 256.41s build, 62/62 steps, 713 compiles).
