# CFA Ethics — Contrastive Minimal-Pairs

A deterministic study feature for the CFA-ethics fork of Anki. It drills the _boundaries_ between
confusable CFA Standards by showing **two near-identical vignettes side by side** that differ by
**exactly one decisive fact** — a fact that flips the answer between **conforms** and **violates**.

There are **no LLM calls at runtime and no AI grading**. The feature is a note type + card
templates + a pure scoring module + a dashboard, all built on the stock Anki engine. It adds **zero
new Rust**, so it ships to AnkiMobile / AnkiDroid automatically through the shared collection & sync.

> **Evidence-grounded mechanism — not a score guarantee.**
> Side-by-side _case comparison_ is one of the better-supported techniques in the learning-science
> literature (Alfieri, Nokes-Malach & Schunn 2013 meta-analysis of contrasting cases, d ≈ 0.50;
> Gentner, Loewenstein & Thompson 2003 on analogical encoding in adult professionals). That evidence
> concerns learning transfer in general; here it is **analogy-transferred** to CFA ethics. We
> therefore describe this as an _evidence-grounded mechanism_. We do **not** claim it is _proven to
> raise CFA exam scores_ — no such study exists for this feature, and the dashboard says so.

## The review flow (3 mandatory steps)

1. **Judge each case** — Conforms / Violates, one click per vignette (both are co-presented on one
   screen, in the same session — never split across days).
2. **Name the decisive fact** — a 4-option multiple-choice: which single difference flips the answer.
   This step is **mandatory**, not optional.
3. **Reveal** — only _after_ the attempt is submitted does the card reveal which **Standard** governs
   (e.g. `I(C) Misrepresentation`) and a short rationale for _why_ the flip happens. The governing
   Standard is never shown before the attempt.

## Deterministic scoring

A pair attempt is **fully correct only if all three sub-answers are right**: both conform/violate
judgments _and_ the named decisive fact. Getting the two judgments right but naming the wrong
decisive fact does **not** count. See [`ethics_scoring.py`](ethics_scoring.py) (`grade_attempt`).

The card auto-rates itself in Anki — **Good** (fully correct) or **Again** (not) — so the review log
faithfully records discrimination. Because the review log syncs, this works across devices.

## The discrimination dashboard (separate from memory)

`ethics_scoring.discrimination_by_cluster` computes, **per confusable-Standard cluster**, the
percentage of your **last N pair attempts** (default 20) that were fully correct. This is a
**discrimination score** — it is deliberately kept **separate from Anki's FSRS memory statistics**
(which measure retention). The two answer different questions: _can you tell the cases apart?_ vs.
_will you remember?_

**Honesty rule:** below a minimum number of attempts in a cluster (default 5) the dashboard shows
**“Not enough data”** rather than a misleadingly precise number, and every scored cluster is shown
with a 95% Wilson confidence interval. The Ethics pairs live in their own sibling deck
**`CFA::Ethics Pairs`**, so their FSRS stats never pollute the main CFA deck.

Two ways to view it:

- **In-app (live):** the add-on ([`__init__.py`](__init__.py)) adds _Tools ▸ CFA Ethics:
  Discrimination Dashboard_, which opens a panel that refreshes after every review.
- **Offline report:** `just cfa-dashboard col=/path/to/collection.anki2` renders a standalone HTML
  report (use when Anki is closed).

## The starter bank

[`pairs.jsonl`](pairs.jsonl) contains **30 verified pairs** across **3 confusable-Standard
clusters** (10 each), stored as reviewable JSON Lines so the bank diff is auditable:

| Cluster (`cluster::` tag)       | Standards drilled                                                             |
| ------------------------------- | ----------------------------------------------------------------------------- |
| `suitability-mnpi-diligence`    | III(C) Suitability · II(A) Material Nonpublic Information · V(A) Diligence    |
| `misrepresentation-attribution` | I(C) Misrepresentation (plagiarism / attribution / performance / credentials) |
| `priority-of-transactions`      | VI(B) Priority of Transactions (personal / beneficial-account flips)          |

All content is **original writing** based on the publicly described CFA Standards of Professional
Conduct. No CFA Institute curriculum text or official/sample questions are copied. Each pair was
drafted against a rubric and then adversarially reviewed on three axes (Standard/answer correctness,
minimality & flip-validity, and distractor quality & originality).

Each JSONL record maps to the note type's fields:

| JSONL key                   | Note field                  |   | JSONL key           | Note field           |
| --------------------------- | --------------------------- | - | ------------------- | -------------------- |
| `pair_id`                   | `PairId`                    |   | `decisive_fact`     | `DecisiveFact`       |
| `cluster`                   | `ClusterTag` (`cluster::…`) |   | `distractors[0..2]` | `DistractorFact1..3` |
| `vignette_a` / `vignette_b` | `VignetteA` / `VignetteB`   |   | `standard`          | `Standard`           |
| `answer_a` / `answer_b`     | `AnswerA` / `AnswerB`       |   | `rationale`         | `Rationale`          |

Each note is tagged with its `los::ethics::…` learning-objective tag, its `cluster::…` tag, and
`ethics::minimal-pair`.

## Quick start

```sh
# 1. validate the bank (no collection needed)
just cfa-validate

# 2. run the tests (scoring rule, per-cluster aggregation, jsonl->notes round-trip)
just cfa-test

# 3. import the 30 pairs into your collection (close Anki first)
just cfa-import col="$HOME/Library/Application Support/Anki2/User 1/collection.anki2"

# 4. install the in-app dashboard add-on (macOS path; see below for others), then `just run`
just cfa-install-addon
```

Add-on folder on other platforms (symlink `cfa/ethics_pairs` → `<base>/addons21/cfa_ethics_pairs`):
Linux `~/.local/share/Anki2`, Windows `%APPDATA%\Anki2`.

## 60-second demo

1. `just run`, open **CFA::Ethics Pairs**, and open _Tools ▸ CFA Ethics: Discrimination Dashboard_
   (it will read **“Not enough data”** for every cluster).
2. Study a pair. Read both vignettes, judge each, and — to show the honest failure mode —
   **deliberately pick a wrong decisive fact**. Submit. The card reveals ✗ _Not fully correct_, the
   governing Standard, and the rationale; it records **Again**.
3. Study a few more pairs correctly. Watch the dashboard tick up from _Not enough data_ to a real
   percentage **with a confidence interval** the moment a cluster crosses the minimum-attempts
   threshold — updating live, separate from the FSRS memory graph.

## Files

| File                                                 | Role                                                                          |
| ---------------------------------------------------- | ----------------------------------------------------------------------------- |
| `pairs.jsonl`                                        | the 30-pair starter bank (auditable)                                          |
| `import_pairs.py`                                    | CLI: jsonl → note type + `CFA::Ethics Pairs` deck + notes (idempotent)        |
| `ethics_notetype.py`                                 | note-type definition + template installer                                     |
| `templates/{front,back}.html`, `templates/style.css` | the interactive review flow (desktop + mobile)                                |
| `ethics_scoring.py`                                  | **pure** deterministic scoring rule + per-cluster aggregation (no `anki` dep) |
| `ethics_revlog.py`                                   | reads pair attempts from the review log                                       |
| `ethics_dashboard.py`                                | discrimination dashboard renderer + offline report CLI                        |
| `__init__.py` + `manifest.json`                      | the in-app dashboard add-on                                                   |
| `tests/`                                             | unit tests (scoring, aggregation, dashboard) + jsonl→notes round-trip         |
| `../../ts/tests/e2e/ethics_pairs_flow.test.ts`       | Playwright flow test (both vignettes; no reveal before attempt)               |
