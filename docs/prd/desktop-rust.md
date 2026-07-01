# Leaf: Desktop build + Rust "mastery query" (agent-1)

## Scope
1. Build the Anki fork from source on macOS end-to-end and launch it.
2. Add ONE real change inside the Rust engine (`rslib/`): a new backend method,
   exposed via a NEW protobuf message, that computes per-topic (deck or tag)
   `{mastered_count, avg_recall}` from the collection, wired through the
   generated bindings so Python (`pylib/`) can call it.
3. Ship `scripts/verify_desktop.sh` (build + full existing test suite + our new
   Rust/Python tests + built-app assertion; exits 0 only if all pass).
4. Docs: `docs/RUST_CHANGE.md`, `BUILD.md`.

## Out-of-scope
- Mobile / AnkiDroid (agent-2), scoring layer (agent-3), shared-engine scouting.
- Editing `docs/prd/INDEX.md` or reading other leaves.
- Any Python/Qt algorithm logic — the mastery computation lives in Rust.
- Sync, UI surfacing of the new query. Backend + bindings + tests only.

## Interfaces (in / out)
- IN: existing Anki build system (`just`, `ninja`/n2, `rust-toolchain.toml`
  pins 1.92.0), collection model in `rslib/` (cards, revlog), protobuf codegen
  in `proto/` → `rslib/`, `pylib/rsbridge`, `_backend.py`.
- OUT (shared contract from INDEX): Rust mastery query returns, per topic,
  `{mastered_count, avg_recall}`, Python-callable. Ships to both platforms via
  the shared Rust core.
  - `mastered_count`: number of cards in the topic considered "mastered"
    (definition to fix in impl slice — candidate: cards in Review queue with
    interval >= threshold, e.g. 21 days).
  - `avg_recall`: mean recall proxy over the topic's cards (candidate: pass
    rate over revlog, or mean of card ease/stability — fix in impl slice).
  - Topic key = deck id (primary); tag support optional/secondary.

## Plan (slices — verify script after each)
1. Toolchain + build gate: install `just`/n2, `just build`, launch check. Write
   `BUILD.md` with exact steps + commit hash.
2. Protobuf message: define request/response in the right `proto/anki/*.proto`,
   run codegen (`just check` or targeted build), confirm generated bindings.
3. Rust impl in `rslib/` + >=3 unit tests (empty deck, all-new cards, mixed).
4. Wire through `pylib` bridge + `_backend.py`; 1 Python test that calls it.
5. `scripts/verify_desktop.sh` + `docs/RUST_CHANGE.md`.

## Done-check
- `bash scripts/verify_desktop.sh` exits 0: builds from source, runs full
  existing test suite, runs our 3 Rust + 1 Python tests, asserts built app
  exists; prints PASS/FAIL summary.
- >=3 Rust unit tests + 1 Python test, all green.
- `docs/RUST_CHANGE.md` (what / why-Rust-not-Python / files touched / merge
  difficulty) and `BUILD.md` (reproducible macOS build+run + commit hash) exist.
- Only `proto/ rslib/ pylib/ qt/(minimal) build/ scripts/ docs/` touched.
- No regressions in the existing test suite.
