# ankiCFA — running & packaging

**Exam:** CFA Level II. Fork of Anki. License: AGPL-3.0-or-later (credit Anki).

## Run from source (development)

```bash
just run            # builds pylib + qt and launches from source
just run-optimized  # release-optimized build
```

Prerequisites are auto-bootstrapped by the build system (uv, node, protoc); you
need Rust (rustup picks up the pinned toolchain in `rust-toolchain.toml`) and a
system Python. See `docs/development.md` / `docs/mac.md`.

Build without launching (used for the day-one gate):

```bash
just build          # ./ninja pylib qt  — produces out/pylib, out/qt, bindings
```

## Clean-machine artifact: wheels + launcher

The official Briefcase `.dmg` path is slow; the documented, prompt-sanctioned
alternative is a **wheels + launcher** bundle that runs on any machine with
Python 3.13+.

1. Build the wheels:

   ```bash
   just wheels        # -> out/wheels/*.whl  (anki, aqt, and deps)
   ```

2. Assemble the bundle:

   ```bash
   mkdir -p dist/wheels
   cp out/wheels/*.whl dist/wheels/
   cp tools/cfa/build_cfa_deck.py dist/
   ```

3. Ship `dist/` (the launcher, `wheels/`, and `build_cfa_deck.py`). On the target
   machine:

   ```bash
   ./launch-ankiCFA.sh              # creates ./anki-venv, installs wheels, launches
   ./launch-ankiCFA.sh --build-deck # also authors the CFA Level II deck + .apkg
   ```

   The first run creates a self-contained virtualenv and installs the wheels; later
   runs launch instantly.

## Authoring the CFA Level II deck

```bash
out/pyenv/bin/python tools/cfa/build_cfa_deck.py --path /path/to/cfa.anki2 \
    --apkg /path/to/CFA-Level-II.apkg
```

Creates the "CFA Level II" deck with `los::<topic>::<reading>` tags across the ten
topic areas and stores the exam date + per-topic weights in the collection config
(which syncs natively). Import the `.apkg` into an existing collection via
**File → Import**.

## Using the CFA features

- **Exam Readiness:** menu **CFA → Exam Readiness…** shows the honest memory score
  (per-topic recall range, coverage %, freshness) or "not enough data" per the
  give-up rule.
- **Exam queue:** `col.sched.build_exam_queue(deck_id=…, days_to_exam=…,
  topic_weights=…)` (or `anki.cfa.build_exam_queue(col, deck_id=…)` using the stored
  config) returns due cards reordered for exam prep — read-only, so FSRS and undo
  are unaffected.
