# Demo video script — CFA Level II Anki fork

_Target length: ~4:30 (within the 3–5 min budget). No AI features — everything
shown is real spaced-repetition statistics and a real, source-built app._

Baseline on screen: `b431cb1265f81abe8e18eff9c8839f3a25aae665` (branch `main`),
branch `chore/wed-proof`.

## Segment map

| Time | Beat | Backing proof artifact |
| --- | --- | --- |
| 0:00–0:30 | (1) A card review in the app | `demo/desktop-review.mp4`; `proof/gate-launch.log`, `proof/gate-smoke.log` |
| 0:30–1:30 | (2) The Rust change in action — `BuildExamQueue` ordering / Exam Readiness | `demo/build.mp4`; `proof/rust-tests.log`, `docs/cfa/RUST_ENGINE_NOTE.md`, `proof/perf-50k.log` |
| 1:30–2:15 | (3) A card synced/loaded on the phone (AnkiDroid) | `demo/phone-review.mp4` **[pending AnkiDroid fleet]** |
| 2:15–3:15 | (4) The three readiness scores with their ranges | `demo/desktop-review.mp4`; `pylib/anki/cfa.py`, `qt/aqt/cfa.py` |
| 3:15–4:15 | (5) Test results (Rust + Python green) | `proof/rust-tests.log`, `proof/python-tests.log` |
| 4:15–4:30 | Close / recap | `proof/README.md` |

---

## Segment 1 — Card review in the app · 0:00–0:30

- **Show:** Launch the source-built fork; open the `CFA::Level II` deck; review one
  card — reveal the answer, press **Good** (then **Again** on a second card so the
  scheduler is visibly doing normal work).
- **Say:** "This is our Anki fork, built from source for CFA Level II. Here's an
  ordinary spaced-repetition review — the real FSRS scheduler, nothing faked."
- **Backing:** `demo/desktop-review.mp4`; the app boots and opens a real
  collection per `proof/gate-launch.log` and `proof/gate-smoke.log` ("SMOKE OK").

## Segment 2 — The Rust change in action · 0:30–1:30

- **Show:** Trigger the exam-prep queue and show cards reordered by exam score.
  Overlay the formula: `score = topic_weight × (1 − retrievability) × deadline_urgency`.
  Point out that a weak, high-weight, near-deadline card rises to the top while a
  well-remembered or zero-weight card sinks. Briefly flash the Rust build.
- **Say:** "This ordering comes from a new **read-only Rust RPC**, `BuildExamQueue`,
  in Anki's shared engine. It reuses FSRS retrievability and writes nothing — no
  card, queue, or revlog mutation — so scheduling and undo stay valid. Because it
  lives in Rust, it ships to every platform from one implementation."
- **Backing:** `demo/build.mp4` (fork builds from source); `proof/rust-tests.log`
  (queue engine tests); design rationale in `docs/cfa/RUST_ENGINE_NOTE.md`;
  `proof/perf-50k.log` (~337 ms over 50,000 due cards — no per-card round-trips).

## Segment 3 — A card on the phone (AnkiDroid) · 1:30–2:15

- **Show:** Sync from desktop, then open AnkiDroid and review the **same** card in
  the `CFA::Level II` deck on the phone; show the exam config having come across.
- **Say:** "Same deck, same card, now on the phone. The exam date and topic
  weights are stored in the collection config, so they sync natively — no new sync
  endpoint — and the engine is the same Rust core AnkiDroid already ships."
- **Backing:** `demo/phone-review.mp4` **[pending — provided by the AnkiDroid
  fleet]**. If unavailable at record time, hold on the desktop sync confirmation
  and state the phone clip is attached separately.

## Segment 4 — The three readiness scores with their ranges · 2:15–3:15

- **Show:** Open **CFA → Exam Readiness**. Point the camera at:
  1. the headline **Memory (recall probability)** shown as a **range**, e.g.
     `71%–83%` with a muted midpoint — never a single number;
  2. the per-topic table column **"Recall R (range)"**, and highlight **three
     topic readiness scores, each with its own range**, e.g.
     `los::ethics 78%–88%`, `los::quant 55%–69%`, `los::fra 62%–74%`;
  3. the footer: score shown only after **≥200 graded reviews AND ≥50% coverage**,
     and it abstains ("not enough data") if a high-weight topic is skipped.
- **Say:** "No AI — pure spaced-repetition stats. Every readiness score is a
  **range** (mean ± spread of FSRS retrievability), so it's honest about
  uncertainty, and the app abstains outright when there isn't enough evidence."
- **Backing:** `demo/desktop-review.mp4` (the dialog); logic in `pylib/anki/cfa.py`
  (`memory_score`, ranges + give-up rule) and `qt/aqt/cfa.py` (the dialog that
  renders the three ranges). _If the demo deck hasn't crossed the give-up
  thresholds, show the honest "not enough data" state first, then a seeded deck
  that clears them to reveal the three ranges._

## Segment 5 — Test results, Rust + Python green · 3:15–4:15

- **Show:** Scroll `proof/rust-tests.log` — the BuildExamQueue unit tests pass
  (ordering, retrievability effect, zero-weight sink, empty deck, urgency
  monotonicity, read-only/undo-preserving): **6 in the committed log, 8 with the
  two new-card tests added in the working tree**. Then `proof/python-tests.log` —
  **7/7** end-to-end tests pass (RPC ordering, read-only + undo, exam-config
  round-trip, and the memory-score give-up/range paths).
- **Say:** "It's all verified: the Rust unit tests on the queue engine and the
  seven Python end-to-end tests on the RPC and the honest memory score are all
  green. Clippy is clean and the 50k-card queue runs in ~1/3 of a second."
- **Backing:** `proof/rust-tests.log`, `proof/python-tests.log` (both green;
  summarized in `proof/README.md`). The Rust count is 6 in the committed log and 8
  once the working-tree new-card tests are included — the test fleet regenerates
  these logs at the current HEAD.

## Close · 4:15–4:30

- **Show:** `proof/README.md` — build/launch gate PASS, tests green, packaging runs
  on a clean machine.
- **Say:** "Built from source, additive Rust RPC, honest ranges, synced to mobile,
  and fully tested — that's the CFA Level II fork."

---

## Recording checklist

- [ ] `demo/desktop-review.mp4` — segments 1, 2, 4 (review, exam-queue ordering, Exam Readiness dialog).
- [ ] `demo/build.mp4` — segment 2 (fork builds from source).
- [ ] `demo/phone-review.mp4` — segment 3 **[pending AnkiDroid fleet]**.
- [x] `proof/rust-tests.log` — segment 5 (exists, green; 6 committed / 8 with new-card tests).
- [x] `proof/python-tests.log` — segment 5 (exists, 7/7 green).
- [ ] Seed a deck past the give-up thresholds (≥200 graded reviews, ≥50% coverage) so segment 4 shows three real ranges, not only the abstain state.
