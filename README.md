# ankiCFA — a study app for the CFA® Level II exam

> **Exam:** **CFA Level II.** ankiCFA is a fork of **[Anki](https://apps.ankiweb.net)**
> (upstream source: <https://github.com/ankitects/anki>).
> **License:** GNU **AGPL-3.0-or-later** — unchanged from Anki (see [LICENSE](./LICENSE)).
> **AI is optional; scores never use AI.** The three honest scores (Memory /
> Performance / Readiness) are pure spaced-repetition statistics from the shared
> Rust engine — identical with AI on or off. An optional AI layer (semantic ethics
> grading and editor card-back drafting) activates only when you supply your own
> `OPENAI_API_KEY`; without a key every AI path falls back to deterministic
> graders. With a key, AI features default **on** but are individually toggleable
> in **CFA → AI Settings…** (settings sync with the collection). No API key and
> no AI-generated content are committed to this repository.

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
- [Due Friday deliverables (D1–D7)](#due-friday-deliverables-d1d7)
- [Submission proof](#submission-proof)
- [Credit to Anki](#credit-to-anki)
- [Upstream Anki README](#anki)

## What this fork adds

Every feature below is **additive** and maps to one of the three theses in
[Brainlift.md](./Brainlift.md): teach ethics as recall through **near-miss
pairs**, schedule for **peak recall on the exam date** rather than indefinite
retention, and **weight cards by topic yield**. The optional AI layer is **OFF by
default** and every AI path has a deterministic fallback, so the app runs fully
without an API key.

- **Exam queue (Rust engine).** A **read-only** backend RPC,
  `SchedulerService.BuildExamQueue`, reorders a deck's due cards by
  `topic_weight × (1 − retrievability) × deadline_urgency`, using FSRS
  retrievability and hierarchical `los::topic::reading` tags. Because it never
  writes, FSRS scheduling and undo history stay valid. Implemented once in the
  shared Rust core so it is available to every platform — see
  [docs/cfa/RUST_ENGINE_NOTE.md](./docs/cfa/RUST_ENGINE_NOTE.md).
- **Exam Readiness — three honest scores, not one overconfident number.** A
  **CFA → Exam Readiness…** menu in the desktop GUI reports **Memory**
  (FSRS retrievability), **Performance** (graded accuracy), and an overall
  **Readiness** score — each as a **range/credible interval** — alongside
  per-topic recall, topic coverage %, and data freshness. An **enforced give-up
  rule** abstains ("not enough data") until **≥ 200 graded reviews**, **≥ 50 %
  topic coverage**, and **≥ 30 first exposures**, and abstains outright if a
  high-weight topic has been skipped. Both desktop and mobile call the **same
  shared Rust RPC** `CollectionService.ComputeCfaScores` (desktop via
  [`pylib/anki/cfa.py`](./pylib/anki/cfa.py), mobile via
  `col.backend.computeCfaScores`) — verified field-by-field to 1e-9 by
  `just cfa-parity-test`. Desktop UI in [`qt/aqt/cfa.py`](./qt/aqt/cfa.py);
  AnkiDroid renders the same three scores natively (see
  [docs/cfa/PLATFORM-MATRIX.md](./docs/cfa/PLATFORM-MATRIX.md)).
- **Ethics minimal-pairs & one-passage cards.** Hand-authored ethics items that
  force the learner to pick a verdict, **highlight the governing evidence**, and
  name the controlling CFA Standard — teaching the _boundary_ between confusable
  Standards, not just the label. Highlights are scored by a deterministic
  span-matching grader with tolerant partial-credit tiers, and the Python and JS
  graders are kept in parity so desktop and mobile grade identically.
- **Optional AI layer (key-gated; toggles default on).** Two AI features, each
  with a deterministic fallback: (1) **semantic grading** of ethics highlights →
  falls back to the span-matching grader; (2) editor **"AI Back"** card-back
  drafting → disabled with a tooltip when AI is off. Effective gate:
  `OPENAI_API_KEY` present **and** master `cfa_ai_enabled` **and** the
  per-feature toggle (`cfa_ai_grading_enabled` / `cfa_ai_tabfill_enabled`) in
  `col.conf` — all default **on**, surfaced in **CFA → AI Settings…**. Every AI
  output carries a **named provenance record** (`source`, `standard`, `item_id`,
  `model`, `rationale`) — see [docs/cfa/AI-PROVENANCE.md](./docs/cfa/AI-PROVENANCE.md).
  **What we skipped:** vector/keyword search over the deck (no RAG), generative
  question authoring, and any AI in the score pipeline. **Eval before serve:**
  `just cfa-ethics-eval` grades 30 human-labeled ethics attempts; LLM must hit
  **≥ 0.80 grade agreement** or the gate fails (see [proof](#submission-proof)).
- **CFA study menu & Peak-on-Exam-Day planner.** The desktop **CFA** menu wires the
  flagship flows end-to-end with no dead-ends — _Study Ethics Minimal-Pairs_,
  _Study Ethics (One-Passage)_, _Study by Exam Priority_, _Exam Readiness…_, and a
  **Peak-on-Exam-Day** deadline view that ranks which cards to prioritize
  (including new cards) so recall peaks on your configured exam date. Each action
  seeds its deck on demand and enters review.
- **UI overhaul.** A shared CFA design system (calm, finance-desk aesthetic
  inspired by markmeldrum.com) restyles the ethics card and the
  readiness/deadline surfaces through SvelteKit web views.
- **CFA Level II deck.** **711 hand-authored, original items** (`license:
  authored-original`, no copyrighted CFA Institute text) spanning **all ten**
  Level II topic areas — ethics, quant, economics, FRA, corporate issuers,
  equity, **fixed income**, **derivatives**, alternative investments, and
  portfolio management — each tagged `los::<topic>::<reading>`. Every built card
  carries a **visible named source** footer (`Source: CFA Level II > <topic> >
  <reading>`), so a study card's provenance mirrors the AI provenance line. Build
  it with [`tools/cfa/build_cfa_deck.py`](./tools/cfa/build_cfa_deck.py); validate
  with [`cfa/deck/validate_deck.py`](./cfa/deck/validate_deck.py). Note: the
  "Study by Exam Priority" queue returns a **capped, weakest-first fetch** (a
  session limit, e.g. 100 on mobile), **not** the deck size — the deck stays
  > 200 cards.
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

The fork's AnkiDroid is branded **ankiCFA** with **native CFA screens** — Ethics
minimal-pairs and the **Exam Readiness** screen (Memory / Performance / Readiness
with ranges, give-up rule, and per-topic recall) call the same
`ComputeCfaScores` engine as desktop. **Two-way sync** uses Anki's native Rust
sync protocol against a self-hosted `anki-sync-server`: review on desktop →
appears on phone and back, with a **more-recent-wins** conflict rule and no
double-counted reviews (`just cfa-sync-test`). **Offline review** queues locally
and merges on reconnect (recorded in [`proof/friday/sync/`](./proof/friday/sync/)).
[docs/cfa/PLATFORM-MATRIX.md](./docs/cfa/PLATFORM-MATRIX.md) is the authoritative
capability matrix.

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

| Layer       | File                                   | CFA change                                                                                        |
| ----------- | -------------------------------------- | ------------------------------------------------------------------------------------------------- |
| proto       | `proto/anki/scheduler.proto`           | +1 RPC (`BuildExamQueue`) + scoring RPC (`ComputeCfaScores`)                                      |
| Rust core   | `rslib/src/scheduler/service/mod.rs`   | `build_exam_queue` + `compute_cfa_scores` (faithful port of `cfa.py`, incl. per-(card,day) dedup) |
| Desktop lib | `pylib/anki/scheduler/v3.py`, `cfa.py` | thin wrappers; `cfa.py` delegates scores to the Rust RPC                                          |
| AI          | `cfa/ai/`, `cfa/ethics_pairs/`         | shared LLM client, semantic ethics grader, eval harness, provenance schema                        |
| Sync        | `pylib/anki/cfa_sync.py`               | local `anki-sync-server` harness + review-conflict rule for round-trip proofs                     |

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

## Due Friday deliverables (D1–D7)

Full acceptance mapping with evidence paths:
[`proof/friday/ACCEPTANCE.md`](./proof/friday/ACCEPTANCE.md). Summary:

| #      | Requirement                              | How we satisfy it                                                                                                                                                                                         | Re-run                                                                                                                          |
| ------ | ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| **D1** | Every AI output traces to a named source | Provenance record on every grade (`source`, `standard`, `item_id`, `model`, `rationale`); example in [`proof/friday/ethics/item5-emitted-payload.json`](./proof/friday/ethics/item5-emitted-payload.json) | inspect card after ethics review                                                                                                |
| **D2** | Eval before students see output; cutoff  | 30 human-labeled ethics attempts; **LLM agreement 0.833 ≥ 0.80 → PASS** ([`proof/friday/phase0/eval-gate-PASS-ai-on-gpt4o.txt`](./proof/friday/phase0/eval-gate-PASS-ai-on-gpt4o.txt))                    | `just cfa-ethics-eval` (needs `OPENAI_API_KEY`)                                                                                 |
| **D3** | Scores work with AI off + in-app toggle  | Scores are AI-free (`ComputeCfaScores`); toggles in **CFA → AI Settings…**                                                                                                                                | `just cfa-parity-test` · `just cfa-ai-toggle-test`                                                                              |
| **D4** | Two-way sync, no lost/double reviews     | Desktop ↔ `anki-sync-server` ↔ phone round-trip; more-recent-wins conflict rule                                                                                                                           | `just cfa-sync-test` · [`proof/friday/sync/roundtrip*.mp4`](./proof/friday/sync/)                                               |
| **D5** | Offline review, sync on reconnect        | Phone reviews offline, full-download on reconnect                                                                                                                                                         | [`proof/friday/sync/offline-then-sync.mp4`](./proof/friday/sync/offline-then-sync.mp4)                                          |
| **D6** | Phone: 3 scores + ranges + give-up       | Native Readiness screen on arm64 emulator                                                                                                                                                                 | [`proof/friday/phase0/mobile-09-readiness.png`](./proof/friday/phase0/mobile-09-readiness.png)                                  |
| **D7** | Eval numbers + phone→desktop recording   | Eval gate log + sync recording                                                                                                                                                                            | eval log above · [`proof/friday/sync/roundtrip-take1-phone-reviews.mp4`](./proof/friday/sync/roundtrip-take1-phone-reviews.mp4) |

### Desktop AI — what, why, skipped

| Built                                | Why                                                                                        | Fallback                                                  |
| ------------------------------------ | ------------------------------------------------------------------------------------------ | --------------------------------------------------------- |
| **Semantic ethics grading** (GPT-4o) | Span-matching misses paraphrased evidence; LLM judges highlight quality against gold spans | Deterministic 4-tier span grader (same tiers, no network) |
| **Tab-to-fill card backs**           | Speed up authoring CFA items in the editor                                                 | Button disabled / tooltip when AI off                     |
| **Shared `cfa/ai/llm_client`**       | One cost-capped, retrying client; never raises                                             | `ok=False` → caller uses fallback                         |

**Skipped:** deck-wide RAG (keyword/vector search), AI-generated questions, AI in
the score pipeline, cloud-hosted keys.

**Eval vs baseline (side-by-side):**

| Grader                     | Grade agreement | Notes                                         |
| -------------------------- | --------------- | --------------------------------------------- |
| Deterministic span matcher | **0.733**       | frozen preview column on the same 30 attempts |
| LLM semantic (GPT-4o)      | **0.833**       | **PASS** at cutoff 0.80                       |

Re-run: `just cfa-ethics-eval` (AI-on gate) · `just cfa-eval` (held-out recall-model
simulation — accuracy 0.686, AUC 0.763 on 30 held-out concepts).

### Mobile sync

- **Forward:** review on desktop → sync → phone shows the review.
- **Reverse:** review on phone → sync → desktop shows it (recorded).
- **Conflict:** same card reviewed on both offline → more-recent timestamp wins; revlog IDs converge with no duplicates.
- **Offline:** reviews queue on device; reconnect triggers sync + full download as needed.

Harness: [`tools/cfa/sync_roundtrip.py`](./tools/cfa/sync_roundtrip.py) ·
[`pylib/anki/cfa_sync.py`](./pylib/anki/cfa_sync.py).

## Submission proof

Build-gate logs, test results, performance measurements, and packaging evidence are
under [`proof/`](./proof). **Friday acceptance bundle:**
[`proof/friday/`](./proof/friday/) — start with
[`ACCEPTANCE.md`](./proof/friday/ACCEPTANCE.md) and [`REPORT.md`](./proof/friday/REPORT.md).
Engine design: [docs/cfa/RUST_ENGINE_NOTE.md](./docs/cfa/RUST_ENGINE_NOTE.md).

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
