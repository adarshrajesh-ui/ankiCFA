# ankiCFA — running & packaging

**Exam:** CFA Level II. Fork of Anki. License: AGPL-3.0-or-later (credit Anki).

## Support matrix & guaranteed launch path

There are two ways to launch, with different support envelopes:

| Path                                               | Platform support                                  | Requirements                                                                            | Guarantee                                                                                                                   |
| -------------------------------------------------- | ------------------------------------------------- | --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **Wheels + `launch-ankiCFA.sh`** (prebuilt bundle) | **Apple-Silicon macOS 12+ only**                  | Native **arm64** `python3`, **Python 3.10+**                                            | Fast, no toolchain. The shipped wheels are `anki-26.5-cp310-abi3-macosx_12_0_arm64` + `aqt-26.5-py3-none-any` — arm64-only. |
| **`just run` from source** (fallback)              | Any platform Anki builds on (macOS/Linux/Windows) | Rust (pinned via `rust-toolchain.toml`) + a system Python; build deps auto-bootstrapped | **Always available** — the guaranteed launch path when the arm64 wheels don't match your machine.                           |

`launch-ankiCFA.sh` validates the interpreter up front (arch `arm64`,
`python3 >= 3.10`, `darwin`) and, on an unsupported setup — Intel/x86_64 mac, an
x86_64 anaconda python under Rosetta, any non-arm64 host, or Python < 3.10 —
refuses to run and prints an actionable error pointing at the `just run`
from-source fallback. A cross-platform (`universal2` / `x86_64`) wheel is **not**
shipped in this minimum-pass bundle; use `just run` on non-arm64 machines.

## Run from source (development)

```bash
just run            # builds pylib + qt and launches from source
just run-optimized  # release-optimized build
```

`just run` is the **guaranteed fallback** whenever the packaged launcher's
platform guard rejects a machine (Intel/x86_64 or any other non-arm64 host, or
Python < 3.10) — see [Support matrix](#support-matrix--guaranteed-launch-path).

Prerequisites are auto-bootstrapped by the build system (uv, node, protoc); you
need Rust (rustup picks up the pinned toolchain in `rust-toolchain.toml`) and a
system Python. See `docs/development.md` / `docs/mac.md`.

Build without launching (used for the day-one gate):

```bash
just build          # ./ninja pylib qt  — produces out/pylib, out/qt, bindings
```

## Clean-machine artifact: wheels + launcher

The official Briefcase `.dmg` path is slow; the documented, prompt-sanctioned
alternative is a **wheels + launcher** bundle for **Apple-Silicon macOS 12+,
Python 3.10+** (see [Support matrix](#support-matrix--guaranteed-launch-path));
on anything else, run from source with `just run` instead.

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
