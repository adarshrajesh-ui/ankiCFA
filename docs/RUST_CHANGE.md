# Rust engine change: per-deck "mastery query"

## What

A new backend method, `GetDeckMastery`, that computes a per-deck study-mastery
summary directly in the Rust engine and exposes it to Python (and, for free, to
every other client that talks to the backend) via the generated protobuf
bindings.

For each non-filtered deck it returns:

| field            | meaning                                                                 |
| ---------------- | ----------------------------------------------------------------------- |
| `deck_id`        | the deck's id                                                           |
| `deck_name`      | human-readable deck name                                                |
| `total_cards`    | number of cards whose home deck is this deck                            |
| `mastered_count` | review-type cards whose interval ≥ **21 days** (`MASTERY_INTERVAL_DAYS`) |
| `avg_recall`     | mean of `(reps - lapses) / reps` over cards reviewed ≥ once (0 if none) |

Cards temporarily pulled into a filtered deck are attributed to their home deck
(`original_deck_id`) so the numbers are stable regardless of study state. Empty
decks appear with zero counts. Results are ordered by `deck_id` for determinism.

The definition of "mastered" and the recall proxy are intentionally simple and
computed from fields already on the `Card` row (`ctype`, `interval`, `reps`,
`lapses`), so the query needs no schema change and no revlog scan.

## Why in Rust, not Python/Qt

- **Single source of truth.** The mastery definition lives once in the engine.
  Desktop (PyQt), AnkiDroid, and any future client get identical numbers over
  the same collection instead of each re-implementing the rule in its own
  language and drifting apart.
- **It's a collection query.** The computation reads the `cards` and `decks`
  tables through the existing storage layer — exactly the kind of work the Rust
  core owns. Doing it in Python would mean pulling every card across the
  FFI/protobuf boundary just to fold it back down to a handful of numbers.
- **Consistency with the codebase.** All other stats (`card_stats`, `graphs`,
  `studied_today`) are computed in `rslib/src/stats/`; this follows the same
  pattern (`Collection` method + `StatsService` impl) rather than inventing a
  new Python-side path.

## Files touched

| File                                   | Change                                                                 |
| -------------------------------------- | ---------------------------------------------------------------------- |
| `proto/anki/stats.proto`               | New `GetDeckMastery` RPC on `StatsService` + `DeckMasteryResponse` msg  |
| `rslib/src/stats/mastery.rs` (new)     | `Collection::deck_mastery()` + 4 unit tests (empty/all-new/mixed/edge)  |
| `rslib/src/stats/mod.rs`               | Register the new `mastery` module                                       |
| `rslib/src/stats/service.rs`           | Wire `StatsService::get_deck_mastery` to `Collection::deck_mastery`     |
| `pylib/tests/test_mastery.py` (new)    | Python test calling `col._backend.get_deck_mastery()`                   |
| `scripts/verify_desktop.sh` (new)      | Build + full suite + our tests + built-app assertion gate               |

Generated bindings (`out/pylib/anki/_backend_generated.py`,
`out/rust/.../backend.rs`, the Rust `anki_proto::stats` structs) are produced by
the build and are **not** hand-edited — adding the RPC to the proto is enough
for `col._backend.get_deck_mastery()` to appear on the Python side.

## Merge difficulty (rebasing on upstream ankitects/anki)

**Low.** The change is additive:

- `stats.proto`: appends one RPC line and one new message; upstream rarely edits
  the `StatsService` RPC list, so conflicts are unlikely and trivial to resolve.
- `stats/mod.rs` / `stats/service.rs`: one-line additions in stable spots.
- `stats/mastery.rs`, `test_mastery.py`, `verify_desktop.sh`: brand-new files,
  no conflict surface.

The only cross-cutting risk is the generated `run_stats_service_method` dispatch
number, which the build regenerates automatically from proto ordinals — nothing
to hand-merge. No existing behaviour, schema, or public API is modified.
