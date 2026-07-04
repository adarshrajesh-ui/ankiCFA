# Why the CFA engine changes live in Rust

_One-page design note for the CFA Level II fork._

The fork adds **three** read-only RPCs to `SchedulerService`, all implemented in
the Rust core (`rslib`) rather than in Python or TypeScript. This note covers
what each one is, **why Rust**, the exact upstream files touched, and the
expected future-merge difficulty. Test counts here are authoritative as of this
run (`cargo test -p anki --lib -- scheduler::cfa_scores scheduler::cfa_deadline
exam_queue` → **24 passed**).

## The three RPCs

### 1. `BuildExamQueue` — exam-prep reordering

Returns the studyable cards of a deck — due (review + learning) cards plus new,
never-reviewed cards — reordered by an exam-prep score:

```
score = topic_weight × (1 − retrievability) × type_multiplier × deadline_urgency
```

- **retrievability (R)** — the FSRS probability of recall right now, from each
  card's memory state; weakness is `1 − R`. New cards have no memory state, so
  they count as maximally weak (`R = 0`) and rise toward the top.
- **topic_weight** — from a caller-supplied map keyed by hierarchical `los::`
  tag prefix (longest-prefix match); a topic with no weight scores 0 and sinks.
- **type_multiplier** — a per-`type::` content-type multiplier (e.g. weight item
  sets over standalone recall) via longest-prefix match; defaults to `1.0`.
- **deadline_urgency** — `1 / max(1, days_to_exam)`; a nearer exam is a global
  scalar, so it changes the numbers, not the relative order.

Returns parallel `card_ids[] / scores[]` sorted by score descending (ties broken
by ascending id for determinism). It **writes nothing**, so FSRS scheduling and
undo history stay valid. **Tests:** 11 in `service/mod.rs`.

### 2. `DeadlineRetention` — peak-on-a-date (DOK-4)

A second, distinct read-only analysis: for a deck + exam date, predict each due
card's FSRS retrievability **at the exam date** and suggest a next interval
**capped at the days remaining**, so no review is ever scheduled past the exam.
Sorted by lowest predicted recall first (weakest-at-the-exam surfaces first),
with an exam-in-the-past guard that caps every interval at 0. This is a
peak-on-a-date computation, not a reshuffle of the `BuildExamQueue` score. It
never mutates card/queue/scheduling state. **Tests:** 10 in `cfa_deadline.rs`.

### 3. `ComputeCfaScores` — the honest three scores

Read-only per-deck scores mirroring `pylib/anki/cfa.py` **exactly**, so desktop
and the AnkiDroid mobile client read identical numbers from one shared engine:

- a give-up-aware **memory** score (exam-weighted FSRS retrievability as a range),
- a first-exposure Wilson **performance** score,
- a coarse logistic **readiness** P(pass), plus the Bayesian readiness "hero"
  band that never abstains (widens instead).

It de-duplicates graded reviews to at most one per `(card, day)` so an offline
dual-device round-trip cannot double-count. Never mutates state. **Tests:** 3 in
`cfa_scores.rs` (empty-collection abstain + Bayesian still answers; happy-path
all-scores; same-day dedup).

## Why Rust, not Python/TypeScript

1. **Shared engine → ships to mobile for free.** The architecture is
   `proto → rslib (Rust core) → pylib (desktop) / rsdroid (AnkiDroid)`. A method
   implemented once on `Collection` in `rslib` is exposed to every platform by
   the same codegen that produces the Python and TypeScript bindings. Putting the
   scoring in Python would strand it on desktop and force a second, drift-prone
   implementation for mobile — the exact failure `ComputeCfaScores` exists to
   prevent (desktop and phone must read *identical* numbers).
2. **They need FSRS internals.** Retrievability comes from
   `FSRS::current_retrievability_seconds(memory_state, elapsed, decay)` and the
   card's `memory_state` / `last_review_time` / `decay` fields — all Rust-side.
   Calling the same API that backs Anki's own `extract_fsrs_retrievability`
   (search/browser sorting) and its retrievability graphs keeps our numbers
   identical to what the app already shows. This applies to all three RPCs.
3. **Performance at 50k cards.** Each RPC is a read-only search + bulk tag query
   + an O(n log n) sort in native code with no per-card RPC round-trips — the
   difference between a snappy call and a UI stall when the benchmark deck reaches
   50,000 cards (see `L1/bench.txt`).
4. **Correctness is testable at the core.** All scoring is unit-tested in Rust
   against real `Collection` state, so the guarantees (read-only, deterministic
   order, dedup) are verified where the logic lives — 24 tests total.

## Exact upstream files touched

| File                                 | Change                                                                                                                                                                          |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `proto/anki/scheduler.proto`         | +3 rpcs on `SchedulerService` (`BuildExamQueue`, `DeadlineRetention`, `ComputeCfaScores`), appended after the last existing rpc; +6 request/response messages. Purely additive. |
| `rslib/src/scheduler/mod.rs`         | +2 module declarations (`mod cfa_deadline; mod cfa_scores;`).                                                                                                                   |
| `rslib/src/scheduler/service/mod.rs` | 3 trait methods (dispatch to inherent impls); inherent `Collection::build_exam_queue` + scoring helpers; 11 exam-queue unit tests. New `use` imports only.                      |
| `rslib/src/scheduler/cfa_deadline.rs`| **New fork-only file** (383 lines): `Collection::deadline_retention` + 10 tests.                                                                                               |
| `rslib/src/scheduler/cfa_scores.rs`  | **New fork-only file** (959 lines): `Collection::compute_cfa_scores` (port of `cfa.py`) + 3 tests.                                                                             |
| `pylib/anki/scheduler/v3.py`         | +1 thin `build_exam_queue(...)` wrapper over the generated binding.                                                                                                            |
| `pylib/anki/cfa_deadline.py`         | **New fork-only file**: thin `deadline_retention(...)` wrapper.                                                                                                                |
| `pylib/anki/cfa.py`                  | **New fork-only file**: exam config, memory/performance/readiness Python reference, `compute_cfa_scores` wrapper.                                                             |

Everything else (`_backend_generated.py`, `out/ts/lib/generated/backend.ts`, the
Rust service trait/dispatch) is **generated** from the proto — no hand edits.
Two of the three RPCs live entirely in **new files**; only `service/mod.rs` and
the proto have in-place edits, and both are additive.

## Expected future-merge difficulty: **low**

- The proto change is **purely additive** — three rpcs appended after the last
  existing rpc, six new messages — so field numbers and method ordering of
  upstream messages are untouched (no wire-compat break). The only realistic
  conflict is textual if upstream appends its own rpc at the same spot; a trivial
  hunk.
- `mod.rs` gains two `mod` lines and `service/mod.rs` edits are additive (new
  methods + helpers + tests) inside the existing `impl` / `#[cfg(test)]` blocks;
  a new upstream method could collide textually but not semantically.
- `v3.py` adds one method in its own section.
- All heavier logic (`cfa_deadline.rs`, `cfa_scores.rs`, `cfa.py`,
  `cfa_deadline.py`) sits in **new files** upstream will never touch — zero
  merge surface.

Net: rebasing onto a newer Anki is expected to be a handful of small, mechanical
conflict resolutions at worst, because we added three leaf RPCs and kept the bulk
of the feature out-of-tree.
