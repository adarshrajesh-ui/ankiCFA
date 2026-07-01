# ankiCFA — a study app for the CFA® Level II exam

> **Exam:** CFA Level II. **This is a fork of [Anki](https://apps.ankiweb.net).**
> **License:** GNU AGPL-3.0-or-later (unchanged from Anki — see [LICENSE](./LICENSE)).
> **No AI:** there are no AI features anywhere in this build — no model calls, no
> generated content, no chatbot. Everything here is deterministic spaced-repetition.

**ankiCFA** adds an exam-prep layer on top of Anki's Rust scheduling engine for
candidates studying for **CFA Level II**:

- **Exam queue (Rust engine).** A read-only backend RPC, `BuildExamQueue`, reorders
  a deck's due cards by `topic_weight × (1 − retrievability) × deadline_urgency`,
  using FSRS retrievability and hierarchical `los::topic::reading` tags. Because it
  never writes, FSRS scheduling and undo stay valid. See
  [docs/cfa/RUST_ENGINE_NOTE.md](./docs/cfa/RUST_ENGINE_NOTE.md).
- **Honest memory score.** Per-topic average FSRS retrievability shown as a **range**
  (mean ± spread), never a single overconfident number, with topic coverage %, the
  freshness of the data, and an **enforced give-up rule**: no score until **≥200
  graded reviews AND ≥50% topic coverage** (otherwise it shows "not enough data"),
  and it **abstains outright if a high-weight topic has been skipped**. Implemented
  in [`pylib/anki/cfa.py`](./pylib/anki/cfa.py).
- **CFA Level II deck.** Hand-authored content spanning the ten topic areas, tagged
  `los::<topic>::<reading>`. Build it with
  [`tools/cfa/build_cfa_deck.py`](./tools/cfa/build_cfa_deck.py).
- **Review loop.** Stock Anki review runs unchanged on the deck.

Running from source and packaging: see [docs/cfa/PACKAGING.md](./docs/cfa/PACKAGING.md).

### Credit to Anki

ankiCFA is built on and forked from **Anki** by Ankitects Pty Ltd and contributors
(<https://apps.ankiweb.net>, <https://github.com/ankitects/anki>). All of Anki's
spaced-repetition engine, scheduler, sync, and UI are Anki's work. This fork adds
only the CFA exam-prep layer described above and retains Anki's AGPL-3.0-or-later
license. The upstream README follows.

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
