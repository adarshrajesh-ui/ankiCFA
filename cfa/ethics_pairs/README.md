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
2. **Highlight the decisive phrase** — in the vignette that makes it a violation, tap the **first
   word** then the **last word** of the deciding phrase (or drag across it). This step is
   **mandatory**, not optional. It works with touch on AnkiDroid because it does **not** rely on
   native text selection — every word is rendered as its own tappable token.
3. **Reveal** — only _after_ the attempt is submitted does the card grade the highlight, reveal the
   **exact gold phrase**, and show which **Standard** governs (e.g. `I(C) Misrepresentation`) plus a
   short rationale for _why_ the flip happens. The governing Standard is never shown before the attempt.

## Deterministic scoring

A pair attempt is **fully correct only if** both conform/violate judgments are right **and** the
highlight of the decisive phrase grades **`correct`**. The highlight is graded by **word-span
overlap** against a stored gold phrase, in three tiers. A single tunable constant
`HIGHLIGHT_CAP_SLACK` (default **5**) sets the width allowance; the cap is `len(gold) + slack`:

- **`correct`** — selection contains **every** gold word **and** is no wider than the cap → _"Correct — you found it."_
- **`somewhat`** — selection contains every gold word **but** is wider than the cap → _"Close — right region, but you only needed these words."_ (does **not** count as fully correct)
- **`wrong`** — selection misses a gold word, is in the wrong vignette, or is empty → _"Not the deciding phrase — here it is."_

The **exact gold phrase is always revealed** after grading. Tokenization + grading live once in
[`ethics_scoring.py`](ethics_scoring.py) (`grade_highlight`) and are mirrored byte-for-byte in the
card template JS; [`tests/test_highlight.py`](tests/test_highlight.py) enforces both the copy match
and a Python↔JS agreement cross-check, so grades are identical on desktop Anki and AnkiDroid.

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

| JSONL key                   | Note field                  |   | JSONL key              | Note field           |
| --------------------------- | --------------------------- | - | ---------------------- | -------------------- |
| `pair_id`                   | `PairId`                    |   | `decisive_fact`        | `DecisiveFact`       |
| `cluster`                   | `ClusterTag` (`cluster::…`) |   | `decisive_phrase`      | `DecisivePhrase`     |
| `vignette_a` / `vignette_b` | `VignetteA` / `VignetteB`   |   | `decisive_phrase_case` | `DecisivePhraseCase` |
| `answer_a` / `answer_b`     | `AnswerA` / `AnswerB`       |   | `distractors[0..2]`    | `DistractorFact1..3` |
| `standard`                  | `Standard`                  |   | `rationale`            | `Rationale`          |

`decisive_phrase` is an **exact verbatim substring** of the vignette named by `decisive_phrase_case`
(`A`/`B`, always the violating vignette) — the importer rejects the bank if it is not, or if it is
not locatable by whitespace tokenization. The legacy `decisive_fact`/`distractors` fields are kept
(additive-only) so older notes and the round-trip test stay valid.

Each note is tagged with its `los::ethics::…` learning-objective tag, its `cluster::…` tag, and
`ethics::minimal-pair`.

## F1 — one-passage multi-span redesign (additive)

A second, self-contained study mode lives beside the minimal-pairs feature (the minimal-pairs
pipeline above is untouched). Instead of two vignettes, the learner reads **one passage**, calls it
**Ethical / Unethical**, and then **highlights every evidence span** that supports that verdict —
**supporting multiple non-contiguous spans**. This is the schema the mobile/AI features (F2+) build on.

- **Bank:** [`passages.jsonl`](passages.jsonl) — the 30 items re-authored to
  `{item_id, cluster, standard, los_tags, verdict, passage, gold_spans[], rationale}`, where each
  `gold_span` is a verbatim `{phrase, token_range, rationale}`. Each Standard was analyzed to mark
  **all** evidence spans (73 spans total; 15 ethical / 15 unethical; every item is multi-span).
- **Deterministic grader (strict; AI-off fallback):** `ethics_scoring.find_gold_spans` /
  `grade_spans` / `grade_passage_attempt`. A span is _found_ when every one of its tokens is
  selected; the grade is `correct` (all spans found, within a per-span width cap), `somewhat` (all
  found but over-wide), `partial` (some but not all found), or `wrong`. A passage attempt is fully
  correct only when the verdict is right **and** the highlight grades `correct`. This strict grader
  still backs `grade_passage_attempt` and the F2 AI-off fallback (below).
- **Deterministic tolerant grader (the displayed card grade):** `ethics_scoring.span_tier` /
  `grade_spans_tolerant` (JS `cfaSpanTier` / `cfaGradeSpansTolerant`). The card grades the highlight
  with partial-credit tolerance so a materially-correct span with imperfect boundaries is not a flat
  `wrong`. Each gold span gets a tier — `full` (every gold token selected; a superset still counts),
  `near` (selection overlaps **≥ half** the gold tokens), or `none` — and the attempt grades
  `correct` (all `full`, within the width cap), `somewhat` (all matched but at least one only `near`,
  or all `full` but over-wide), `partial` (some but not all spans matched), or `wrong` (no span
  matched, or empty). It is fully offline and deterministic (no LLM), mirrors the desktop F2
  tolerance, and never downgrades a strict `correct`.
- **Card:** [`templates/passage_front.html`](templates/passage_front.html) +
  [`passage_back.html`](templates/passage_back.html). The tokenizer + both multi-span graders (strict
  and tolerant) are mirrored byte-for-byte between the template JS,
  [`tests/js/passage_logic.js`](tests/js/passage_logic.js), and Python, so grades are identical on
  desktop Anki and AnkiDroid. Once the attempt is complete (verdict picked, evidence highlighted,
  **Check answer** pressed), the front persists the full completed-attempt payload to `localStorage`,
  so pressing Anki's built-in **Show Answer** on the back reveals the same governing Standard +
  rationale (and per-span breakdown, including `near` matches) as the front reveal — never the
  "Attempt not completed" dead-end. The back still carries **no** answer-key text in its markup, so a
  reflexive Show Answer _before_ completing an attempt still cannot leak the answer.
- **Validation + import:** [`passages.py`](passages.py) validates the bank (verbatim,
  token-locatable, non-overlapping spans; the union of spans must itself grade `correct`) and imports
  it into a sibling deck **`CFA::Ethics Passages`** with note type **`CFA Ethics One-Passage`**.

```sh
just cfa-passages-validate   # validate the bank (no collection)
just cfa-passages-test       # grader + schema + Python<->JS parity + importer round-trip
```

Proof (rendered card, real driven attempts): `proof/gnhf2/f1-psg17-fullycorrect.png` (verdict +
three non-contiguous spans → fully correct) and `proof/gnhf2/f1-psg04-partial.png` (correct verdict
but only 2 of 3 spans → honest _partial_).

## F2 — semantic AI grading of the highlight (additive, AI-off safe)

The deterministic graders are literal token-overlap. The tolerant grader (F1, above) already gives
**partial credit** for a different-boundary highlight — e.g. _"unreleased quarterly earnings"_ when
the gold phrase is _"exact unreleased quarterly earnings figure"_ scores `partial` (a `near` match)
rather than a flat `wrong` — but it still cannot recognize a genuine **paraphrase** or upgrade such
an attempt to fully correct. F2 adds a **semantic** grade on top, with tolerance for paraphrase and
different boundaries.

- **Grader:** [`ai_grading.py`](ai_grading.py) — `grade_semantic(passage, answer_verdict,
  judged_verdict, gold_spans, learner_spans)` sends the attempt through
  [`cfa/ai/llm_client.py`](../ai/llm_client.py) and asks the model to judge, WITH an explicit error
  margin, whether the learner's spans cover each gold piece of evidence. It returns
  `{grade, correct, explanation, per_span[]}` plus `source: "ai" | "fallback"`.
- **AI-OFF contract:** no key, a network error, the cost cap, or an unparseable reply all mean
  `grade_semantic` returns the **exact strict F1 deterministic grade** (`grade_spans`) with
  `source == "fallback"`. It never
  raises, and the API key never enters the prompt or the result. The verdict correctness is always
  computed by string equality (never trusted to the model).
- **Desktop bridge:** [`qt/aqt/cfa_ethics_ai.py`](../../qt/aqt/cfa_ethics_ai.py) registers a
  `webview_did_receive_js_message` handler. The card JS keeps its own deterministic grade (so
  AnkiDroid / AI-off lose nothing), then calls `pycmd("cfaGradeEthics:" + payload, cb)`; when the
  LLM actually graded, an **AI feedback** block is appended showing the semantic grade + what was
  nailed/missed. Registered from `aqt.cfa.setup_menu`.
- **Eval:** [`eval_ai_grading.py`](eval_ai_grading.py) over the 30 human-labeled attempts in
  [`eval_attempts.jsonl`](eval_attempts.jsonl) (authored by [`build_eval_attempts.py`](build_eval_attempts.py);
  8 are "semantic-win" cases where the deterministic grader under-scores). With `OPENAI_API_KEY` set
  it asserts LLM grade-agreement ≥ 0.80; **AI-off it prints the deterministic baseline (0.733) and
  skips the LLM assertion** — the honest AI-off number, not a faked pass.

```sh
just cfa-ai-grade-test   # pure grader tests (mocked LLM + AI-off fallback) + the desktop bridge tests
just cfa-ethics-eval     # AI-off: deterministic baseline; with a key: asserts LLM agreement >= 0.8
```

Proof: `proof/gnhf2/f2-psg01-ai.png` (a driven attempt whose clipped spans grade deterministically
`wrong` — "0 of 2 found" — while the AI feedback block upgrades it to _Correct_ with per-span
explanations), `proof/gnhf2/f2-psg01-aioff.png` (same attempt with AI OFF: no AI block, the
deterministic reveal stands), and `proof/gnhf2/f2-eval-report.txt` (the AI-off eval run).

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
   **deliberately highlight the wrong phrase** (or the right region but far too many words). Submit.
   The card reveals ✗ _Not fully correct_, the true gold phrase, the governing Standard, and the
   rationale; it records **Again**.
3. Study a few more pairs correctly. Watch the dashboard tick up from _Not enough data_ to a real
   percentage **with a confidence interval** the moment a cluster crosses the minimum-attempts
   threshold — updating live, separate from the FSRS memory graph.

## Files

| File                                                 | Role                                                                                                                 |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `pairs.jsonl`                                        | the 30-pair starter bank (auditable)                                                                                 |
| `import_pairs.py`                                    | CLI: jsonl → note type + `CFA::Ethics Pairs` deck + notes (idempotent)                                               |
| `ethics_notetype.py`                                 | note-type definition + template installer                                                                            |
| `templates/{front,back}.html`, `templates/style.css` | the interactive tap-to-highlight review flow (desktop + mobile)                                                      |
| `ethics_scoring.py`                                  | **pure** scoring: tokenize / `find_gold_indices` / `grade_highlight` / `grade_attempt` + aggregation (no `anki` dep) |
| `ethics_revlog.py`                                   | reads pair attempts from the review log                                                                              |
| `ethics_dashboard.py`                                | discrimination dashboard renderer + offline report CLI                                                               |
| `__init__.py` + `manifest.json`                      | the in-app dashboard add-on                                                                                          |
| `tests/`                                             | unit tests (scoring, highlight grading, aggregation, dashboard), jsonl→notes round-trip                              |
| `tests/js/`                                          | standalone copy of the template's highlight logic + Node harness for the Python↔JS parity test                       |
| `../../ts/tests/e2e/ethics_pairs_flow.test.ts`       | Playwright flow test (both vignettes; no reveal before attempt)                                                      |
