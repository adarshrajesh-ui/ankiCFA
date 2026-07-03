# ankiCFA — a study app for the CFA® Level II exam

> **Exam:** **CFA Level II.** ankiCFA is a fork of **[Anki](https://apps.ankiweb.net)**
> (upstream source: <https://github.com/ankitects/anki>).
> **License:** GNU **AGPL-3.0-or-later** — unchanged from Anki (see [LICENSE](./LICENSE)).
> **AI is optional and OFF by default.** The core study experience is fully
> deterministic spaced repetition and makes no network calls. An optional AI layer
> (semantic grading of ethics highlights and editor card-back drafting) activates
> only when you supply your own `OPENAI_API_KEY`; with no key the app falls back to
> the deterministic graders and behaves exactly like an AI-free build. No API key
> and no AI-generated content are committed to this repository.

**ankiCFA** adds a thin **exam-prep layer** on top of Anki's Rust scheduling engine
for candidates studying for the **CFA Level II** exam. Anki's spaced-repetition
engine, scheduler, sync, and user interface are all the work of the Anki authors;
this fork adds only the CFA features described below and retains Anki's
AGPL-3.0-or-later license.

The desktop app lives in **this repository (`ankiCFA`)**. The companion mobile app
is built from a separate **AnkiDroid** fork and shares the same Rust engine — see
[Building & running](#building--running).

## Contents

- [What this fork adds](#what-this-fork-adds)
- [Building & running](#building--running)
  - [Prerequisites](#prerequisites)
  - [Desktop (this repo — ankiCFA)](#desktop-this-repo--ankicfa)
  - [Mobile (AnkiDroid fork)](#mobile-ankidroid-fork)
- [Architecture overview](#architecture-overview)
- [CFA feature details](#cfa-feature-details)
- [Submission proof](#submission-proof)
- [Credit to Anki](#credit-to-anki)
- [Upstream Anki README](#anki)

## What this fork adds

- **Exam queue (Rust engine).** A **read-only** backend RPC,
  `SchedulerService.BuildExamQueue`, reorders a deck's due cards by
  `topic_weight × (1 − retrievability) × deadline_urgency`, using FSRS
  retrievability and hierarchical `los::topic::reading` tags. Because it never
  writes, FSRS scheduling and undo history stay valid. Implemented once in the
  shared Rust core so it is available to every platform — see
  [docs/cfa/RUST_ENGINE_NOTE.md](./docs/cfa/RUST_ENGINE_NOTE.md).
- **Exam Readiness — an honest memory score.** A **CFA → Exam Readiness…** menu in
  the desktop GUI reports per-topic average FSRS retrievability as a **range**
  (mean ± spread) rather than a single overconfident number, alongside topic
  coverage %, data freshness, and an **enforced give-up rule**: no score until
  **≥ 200 graded reviews AND ≥ 50 % topic coverage** (otherwise it shows "not
  enough data"), and it **abstains outright if a high-weight topic has been
  skipped**. Implemented in [`pylib/anki/cfa.py`](./pylib/anki/cfa.py) with the UI
  in [`qt/aqt/cfa.py`](./qt/aqt/cfa.py).
- **CFA Level II deck.** Hand-authored content spanning the eight topic areas, tagged
  `los::<topic>::<reading>`. Build it with
  [`tools/cfa/build_cfa_deck.py`](./tools/cfa/build_cfa_deck.py).
- **Stock review loop.** Standard Anki review runs unchanged on the deck.

## Building & running

### Prerequisites

Clone the repo into a path that contains **no spaces**. On all platforms you need:

- **Rust** via [rustup](https://rustup.rs/). The pinned toolchain in
  `rust-toolchain.toml` is downloaded automatically.
- **Ninja** or **N2** (N2 gives nicer progress output). Install N2 with
  `tools/install-n2`, or use system/homebrew Ninja (1.10+).
- A **system Python** (3.9+ recommended). The build auto-bootstraps the remaining
  tooling (`uv`, Node, `protoc`) into `out/`.
- _(Recommended)_ the [`just`](https://just.systems/) command runner
  (`brew install just` or `uv tool install just`). All commands below use `just`;
  the underlying `./ninja` / `./run` invocations are shown where useful.

Platform-specific notes: [docs/mac.md](./docs/mac.md),
[docs/windows.md](./docs/windows.md), [docs/linux.md](./docs/linux.md). More detail
in [docs/development.md](./docs/development.md).

### Desktop (this repo — ankiCFA)

```bash
# Build the desktop app (Rust core + protobuf codegen + web pages + pylib + qt).
just build              # == ./ninja pylib qt

# Build and launch Anki from source in development mode.
just run

# Launch against a specific data/profile folder (e.g. a throwaway test profile),
# so you don't touch your real Anki data.
ANKI_BASE=/tmp/ankiCFA-data just run

# Release-optimized build (slower to compile, faster to run).
just run-optimized

# Format, build, lint, and run the full test suite (do this before submitting).
just check              # == ./ninja pylib qt check
```

Redistributable wheels and a clean-machine launcher (`just wheels` +
`dist/launch-ankiCFA.sh`) are documented in
[docs/cfa/PACKAGING.md](./docs/cfa/PACKAGING.md). Run `just --list` to see every
recipe.

### Mobile (AnkiDroid fork)

> **Maintained by the AnkiDroid fleet — separate repository.**

The mobile app is **not** built from this repository. It is produced from a fork of
**[AnkiDroid](https://github.com/ankidroid/Anki-Android)**, the official Android
client, which embeds the **same Rust core** (`rslib`) through the `rsdroid` bridge.
Because the CFA scheduling logic lives in that shared Rust core, the exam-queue
engine is available to the mobile app without a second implementation.

At a high level the AnkiDroid fork follows the standard AnkiDroid Android/Gradle
build: the Rust backend is compiled for Android and packaged with the Kotlin/Java
app into an APK. **Exact build commands, toolchain versions, and CFA-specific mobile
wiring are owned and documented by the AnkiDroid fleet in that fork's own README**
— refer to it for the authoritative mobile build steps.

## Architecture overview

Anki (and therefore ankiCFA) is a layered system whose non-Rust APIs are all
defined once in Protobuf and generated into each language:

```
              proto/  (service + message definitions, the cross-language API)
                │  codegen
                ▼
          rslib/  (Rust core engine: collection, scheduler, FSRS, sync)
                │  same engine, two bridges
     ┌──────────┴───────────┐
     ▼                      ▼
pylib/ (desktop)      rsdroid  →  AnkiDroid (mobile)
Python wrapper +      Rust bridge compiled for Android
rsbridge (PyO3)       (separate AnkiDroid fork)
     │
     ▼
qt/aqt/  (PyQt desktop GUI, embeds the web components)
     ▲
     │  served web assets
ts/ + sass/  (Svelte / TypeScript web components: editor, reviewer, deck config…)
```

- **`proto/`** — Protobuf definitions that describe the backend's RPCs and messages;
  the build generates matching Rust, Python, and TypeScript bindings so every layer
  talks to the core in a type-safe way.
- **`rslib/`** — the Rust core engine (collection, scheduler, FSRS, media, sync).
  This is where the heavy logic lives.
- **`pylib/`** — the Python library that wraps the Rust core for the desktop, with
  the `rsbridge` PyO3 module exposing it to Python.
- **`qt/aqt/`** — the PyQt desktop application, which embeds Anki's web components.
- **`ts/` + `sass/`** — the Svelte/TypeScript web frontend (reviewer, editor, deck
  options, etc.), served to the desktop and mobile web views.
- **`rsdroid` → AnkiDroid** — the mobile app reuses the same `rslib` core via the
  `rsdroid` bridge, so an engine change ships to Android too (built from the
  separate AnkiDroid fork).

### Where the CFA additions live

The fork keeps its merge surface deliberately small. Almost all CFA logic sits in
**new, fork-only files** that upstream Anki will never touch; only three existing
files receive small, additive edits:

| Layer       | File                                 | CFA change                                                                                        |
| ----------- | ------------------------------------ | ------------------------------------------------------------------------------------------------- |
| proto       | `proto/anki/scheduler.proto`         | +1 RPC and +2 messages (`BuildExamQueue{Request,Response}`), appended after the last existing RPC |
| Rust core   | `rslib/src/scheduler/service/mod.rs` | `Collection::build_exam_queue` + scoring helpers + unit tests                                     |
| Desktop lib | `pylib/anki/scheduler/v3.py`         | one thin wrapper over the generated binding                                                       |

New fork-only files (no upstream merge surface):
[`pylib/anki/cfa.py`](./pylib/anki/cfa.py) (exam config + memory score),
[`qt/aqt/cfa.py`](./qt/aqt/cfa.py) (Exam Readiness UI),
[`tools/cfa/`](./tools/cfa) (deck authoring),
`pylib/tests/test_cfa.py`, and [`docs/cfa/`](./docs/cfa). Everything under `out/`
(`_backend_generated.py`, `backend.ts`, the Rust service dispatch) is generated from
the proto — no hand edits. See
[docs/cfa/RUST_ENGINE_NOTE.md](./docs/cfa/RUST_ENGINE_NOTE.md) for the full rationale
and merge-difficulty analysis.

## CFA feature details

- **Exam queue:** `col.sched.build_exam_queue(deck_id=…, days_to_exam=…,
  topic_weights=…)`, or `anki.cfa.build_exam_queue(col, deck_id=…)` to use the exam
  date and weights stored in the collection config. Returns due cards reordered for
  exam prep; read-only, so FSRS state and undo are unaffected.
- **Exam Readiness:** menu **CFA → Exam Readiness…** shows the honest memory score
  (per-topic recall range, coverage %, freshness) or "not enough data" per the
  give-up rule.
- **Deck authoring & packaging:** see
  [docs/cfa/PACKAGING.md](./docs/cfa/PACKAGING.md).

## Submission proof

Build-gate logs, test results, performance measurements, and packaging evidence for
this submission are collected under [`proof/`](./proof) (start with
[proof/README.md](./proof/README.md) and [proof/GATE.md](./proof/GATE.md)). The
one-page engine design note is [docs/cfa/RUST_ENGINE_NOTE.md](./docs/cfa/RUST_ENGINE_NOTE.md).

## Credit to Anki

ankiCFA is built on and forked from **Anki** by Ankitects Pty Ltd and contributors
(<https://apps.ankiweb.net>, <https://github.com/ankitects/anki>). All of Anki's
spaced-repetition engine, scheduler, sync, and UI are Anki's work. This fork adds
only the CFA exam-prep layer described above and retains Anki's AGPL-3.0-or-later
license. The list of Anki contributors is in [CONTRIBUTORS](./CONTRIBUTORS); the
upstream project's README follows below.

> _CFA® is a registered trademark of CFA Institute. ankiCFA is an independent,
> open-source study aid and is not affiliated with, endorsed by, or sponsored by
> CFA Institute._

---

# Anki

[![Build Status](https://github.com/ankitects/anki/actions/workflows/ci.yml/badge.svg)](https://github.com/ankitects/anki/actions/workflows/ci.yml)
[![Documentation](https://img.shields.io/badge/docs-dev--docs.ankiweb.net-blue)](https://dev-docs.ankiweb.net)

This repo contains the source code for the computer version of
[Anki](https://apps.ankiweb.net).

## About

Anki is a spaced repetition program. Please see the [website](https://apps.ankiweb.net) to learn more.

## Getting Started

### Contributing

Want to contribute to Anki? Check out the [Contribution Guidelines](./docs/contributing.md).

For more information on building and developing, please see [Development](./docs/development.md).

#### Contributors

The following people have contributed to Anki: [CONTRIBUTORS](./CONTRIBUTORS)

### Anki Betas

If you'd like to try development builds of Anki but don't feel comfortable
building the code, please see [Anki betas](https://betas.ankiweb.net/).

## License

Anki's license: [LICENSE](./LICENSE)
