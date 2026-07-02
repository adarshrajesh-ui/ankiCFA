# Why `BuildExamQueue` lives in the Rust engine

_One-page design note for the CFA Level II fork._

## What it is

A new, **read-only** backend RPC, `SchedulerService.BuildExamQueue`, that returns
the studyable cards of a deck — its due (review + learning) cards plus new,
never-reviewed cards — reordered by an exam-prep score:

```
score = topic_weight × (1 − retrievability) × deadline_urgency
```

- **retrievability (R)** — the FSRS probability of recall right now, computed
  from each card's memory state; weakness is `1 − R`. New, never-reviewed cards
  have no memory state, so they count as maximally weak (`R = 0`) and naturally
  rise toward the top.
- **topic_weight** — from a caller-supplied map keyed by hierarchical `los::`
  tag prefix (longest-prefix match); a topic with no weight scores 0 and sinks.
- **deadline_urgency** — `1 / max(1, days_to_exam)`, so a nearer exam lifts every
  score. It is a global scalar, so it changes the numbers, not the relative order.

It returns parallel `card_ids[] / scores[]` sorted by score descending (ties
broken by ascending id for determinism). It **writes nothing** — no card, queue,
revlog, or config mutation — so FSRS scheduling and the undo history stay valid.

## Why Rust, not Python/TypeScript

1. **Shared engine → ships to mobile for free.** The architecture is
   `proto → rslib (Rust core) → pylib (desktop) / rsdroid (AnkiDroid)`. A method
   implemented once on `Collection` in `rslib` is exposed to every platform by
   the same codegen that produces the Python and TypeScript bindings. Putting the
   scoring in Python would strand it on desktop and force a second, drift-prone
   implementation for mobile.
2. **It needs FSRS internals.** Retrievability comes from
   `FSRS::current_retrievability_seconds(memory_state, elapsed, decay)` and the
   card's `memory_state` / `last_review_time` / `decay` fields — all Rust-side.
   Calling the same `current_retrievability_seconds` API that backs Anki's own
   `extract_fsrs_retrievability` (search/browser sorting) and its retrievability
   graphs keeps our numbers identical to what the app already shows.
3. **Performance at 50k cards.** Gathering is one read-only search
   (`deck:… (is:due or is:new)`), one bulk tag query, and an O(n log n) sort —
   all in native code with no per-card RPC round-trips. This is the difference
   between a snappy call and a UI stall when the benchmark deck reaches 50,000
   cards.
4. **Correctness is testable at the core.** The scoring is unit-tested in Rust
   against real `Collection` state, so the guarantee (read-only, deterministic
   order) is verified where the logic lives.

## Exact upstream files touched

| File                                 | Change                                                                                                                   |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| `proto/anki/scheduler.proto`         | +1 rpc on `SchedulerService`; +2 messages (`BuildExamQueueRequest`, `BuildExamQueueResponse`).                           |
| `rslib/src/scheduler/service/mod.rs` | Trait method + inherent `Collection::build_exam_queue`; 3 private scoring helpers; 8 unit tests. New `use` imports only. |
| `pylib/anki/scheduler/v3.py`         | +1 thin `build_exam_queue(...)` wrapper over the generated binding.                                                      |

Everything else (`_backend_generated.py`, `out/ts/lib/generated/backend.ts`, the
Rust service trait/dispatch) is **generated** from the proto — no hand edits.

New, fork-only files (no merge surface): `pylib/anki/cfa.py` (exam config +
memory score), `qt/aqt/cfa.py` (UI), `tools/cfa/`, `pylib/tests/test_cfa.py`.

## Expected future-merge difficulty: **low**

- The proto change is **purely additive** and appended after the last existing
  rpc, so field numbers and method ordering of upstream messages are untouched —
  no wire-compat break. The only realistic conflict is a textual one if upstream
  appends its own rpc at the same spot; that is a trivial hunk to resolve.
- `service/mod.rs` edits are additive (new method + helpers + tests) inside the
  existing `impl` and `#[cfg(test)]` blocks; a new upstream method could collide
  textually but not semantically.
- `v3.py` adds one method in its own section.
- All heavier logic sits in **new files** upstream will never touch.

Net: rebasing onto a newer Anki is expected to be a handful of small, mechanical
conflict resolutions at worst, because we added a leaf RPC and kept the rest of
the feature out-of-tree.
