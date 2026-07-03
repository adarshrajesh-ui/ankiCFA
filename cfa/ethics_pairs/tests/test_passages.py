# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Tests for the F1 ONE-PASSAGE multi-span redesign: the deterministic multi-span grader, the
passages.jsonl schema/answer-key validation, and a Python<->JS agreement cross-check so the same
grades are produced in the passage card template (desktop Anki + AnkiDroid webviews) as in the pure
Python scorer.

No ``anki`` dependency; the Node cross-check is skipped if ``node`` is not on PATH.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, PKG)

import passages as P  # noqa: E402
from ethics_scoring import (  # noqa: E402
    ETHICAL,
    SPAN_CAP_SLACK,
    UNETHICAL,
    PassageAttempt,
    find_gold_spans,
    grade_passage_attempt,
    grade_spans,
    grade_spans_tolerant,
    span_cap,
    span_tier,
)

FRONT = os.path.join(PKG, "templates", "passage_front.html")
PASSAGES = os.path.join(PKG, "passages.jsonl")
JS_LOGIC = os.path.join(HERE, "js", "passage_logic.js")
JS_RUNNER = os.path.join(HERE, "js", "run_span_matrix.js")
NODE = shutil.which("node")


# ------------------------------------------------------------------- grade_spans tiers


def test_all_spans_found_within_cap_is_correct():
    assert grade_spans([1, 2, 5, 6], [[1, 2], [5, 6]])["grade"] == "correct"


def test_all_spans_found_but_too_wide_is_somewhat():
    # two gold spans -> cap = 4 gold tokens + 4*2 = 12; a 15-word blob is over the cap.
    res = grade_spans(list(range(0, 15)), [[1, 2], [5, 6]])
    assert res["grade"] == "somewhat" and res["found"] == 2


def test_some_but_not_all_spans_found_is_partial():
    res = grade_spans([1, 2], [[1, 2], [5, 6]])
    assert res["grade"] == "partial"
    assert res["found"] == 1 and res["total"] == 2
    assert res["per_span"] == [True, False]


def test_no_span_found_is_wrong():
    assert grade_spans([90, 91], [[1, 2], [5, 6]])["grade"] == "wrong"


def test_empty_selection_is_wrong():
    assert grade_spans([], [[1, 2], [5, 6]])["grade"] == "wrong"


def test_partial_coverage_of_a_span_does_not_count_it():
    # selection has 1 (part of span A) and all of span B, but not 2 -> A not fully covered.
    res = grade_spans([1, 5, 6], [[1, 2], [5, 6]])
    assert res["per_span"] == [False, True] and res["grade"] == "partial"


def test_unordered_selection_is_handled():
    assert grade_spans([6, 2, 1, 5], [[1, 2], [5, 6]])["grade"] == "correct"


def test_single_span_behaves_like_a_contiguous_highlight():
    assert grade_spans([3, 4, 5], [[3, 4, 5]])["grade"] == "correct"


def test_span_cap_scales_with_number_of_spans():
    assert SPAN_CAP_SLACK == 4
    assert span_cap(4, 1) == 4 + 4 * 1
    assert span_cap(4, 2) == 4 + 4 * 2
    # n_spans floored at 1 so a zero-span cap never underflows.
    assert span_cap(3, 0) == 3 + 4


def test_custom_cap_overrides_default():
    assert grade_spans([1, 2, 3, 4], [[1, 2], [3, 4]], cap=4)["grade"] == "correct"
    assert grade_spans([0, 1, 2, 3, 4], [[1, 2], [3, 4]], cap=4)["grade"] == "somewhat"


# ------------------------------------------------- Item 2: partial-credit tolerant grader tiers


def test_span_tier_full_near_none():
    assert span_tier({1, 2, 3}, [1, 2, 3]) == "full"
    assert span_tier({1, 2, 3, 4}, [1, 2, 3]) == "full"  # a superset still counts as full
    assert span_tier({1, 2}, [1, 2, 3]) == "near"  # 2 of 3 (>= half)
    assert span_tier({1, 2}, [1, 2, 3, 4]) == "near"  # 2 of 4 (exactly half)
    assert span_tier({1}, [1, 2]) == "near"  # 1 of 2 (exactly half)
    assert span_tier({1}, [1, 2, 3]) == "none"  # 1 of 3 (below half)
    assert span_tier({9}, [1, 2, 3]) == "none"  # no overlap
    assert span_tier(set(), []) == "none"


def test_tolerant_all_full_within_cap_is_correct():
    res = grade_spans_tolerant([1, 2, 5, 6], [[1, 2], [5, 6]])
    assert res["grade"] == "correct" and res["found"] == 2 and res["near"] == 0
    assert res["per_span"] == ["full", "full"]


def test_tolerant_all_full_but_too_wide_is_somewhat():
    res = grade_spans_tolerant(list(range(0, 15)), [[1, 2], [5, 6]])
    assert res["grade"] == "somewhat" and res["found"] == 2


def test_tolerant_all_matched_but_some_near_is_somewhat():
    # span A fully covered, span B only overlapping (2 of 3) -> all matched, not all full -> somewhat
    res = grade_spans_tolerant([1, 2, 5, 6], [[1, 2], [5, 6, 7]])
    assert res["per_span"] == ["full", "near"]
    assert res["grade"] == "somewhat" and res["found"] == 1 and res["near"] == 1


def test_tolerant_one_span_missed_is_partial():
    res = grade_spans_tolerant([1, 2], [[1, 2], [5, 6]])
    assert res["grade"] == "partial" and res["found"] == 1 and res["near"] == 0
    assert res["per_span"] == ["full", "none"]


def test_tolerant_near_only_still_partial_not_wrong():
    # selection materially overlaps span A (2 of 3) but nothing of span B -> partial, not wrong
    res = grade_spans_tolerant([1, 2], [[1, 2, 3], [5, 6]])
    assert res["per_span"] == ["near", "none"]
    assert res["grade"] == "partial" and res["found"] == 0 and res["near"] == 1


def test_tolerant_no_material_overlap_is_wrong():
    assert grade_spans_tolerant([90, 91], [[1, 2], [5, 6]])["grade"] == "wrong"
    # a single token of a 3-token span is below the half threshold -> not credited
    assert grade_spans_tolerant([1], [[1, 2, 3], [5, 6]])["grade"] == "wrong"


def test_tolerant_empty_selection_is_wrong():
    assert grade_spans_tolerant([], [[1, 2], [5, 6]])["grade"] == "wrong"


def test_tolerant_never_downgrades_a_strict_correct():
    # Any selection the strict grader calls fully correct must also be tolerant-correct.
    for sel, gold in ([1, 2, 5, 6], [[1, 2], [5, 6]]), ([3, 4, 5], [[3, 4, 5]]):
        assert grade_spans(sel, gold)["grade"] == "correct"
        assert grade_spans_tolerant(sel, gold)["grade"] == "correct"


def test_tolerant_psg01_unreleased_quarterly_earnings_is_partial_not_wrong():
    # The Item 2 symptom, verbatim: highlighting "unreleased quarterly earnings" on the Priya/MNPI
    # passage (gold span 1 is "exact unreleased quarterly earnings figure") scored a flat "wrong"
    # under the strict grader; the tolerant grader gives partial credit for the materially-correct
    # (3-of-5-token) highlight.
    rows = {r["item_id"]: r for r in _load_raw()}
    p = rows["PSG-01"]
    phrases = [g["phrase"] for g in p["gold_spans"]]
    runs = find_gold_spans(p["passage"], phrases)
    sel = find_gold_spans(p["passage"], ["unreleased quarterly earnings"])[0]
    assert sel, "sanity: the learner's near-miss phrase is token-locatable"
    assert grade_spans(sel, runs)["grade"] == "wrong"  # the old harsh behavior
    tol = grade_spans_tolerant(sel, runs)
    assert tol["grade"] == "partial"  # Item 2 fix: materially-correct -> partial credit
    assert tol["per_span"][0] == "near" and tol["per_span"][1] == "none"
    assert tol["found"] == 0 and tol["near"] == 1


def test_tolerant_bank_perfect_selection_still_correct():
    # The authored answer key (perfect selection) must remain fully correct under tolerance too.
    for r in _load_raw():
        phrases = [g["phrase"] for g in r["gold_spans"]]
        runs = find_gold_spans(r["passage"], phrases)
        perfect = [i for run in runs for i in run]
        assert grade_spans_tolerant(perfect, runs)["grade"] == "correct", r["item_id"]


# -------------------------------------------------------------------- find_gold_spans


def test_find_gold_spans_locates_multiple_noncontiguous_phrases():
    passage = (
        "Priya received the exact figure and then sold the client position quietly."
    )
    runs = find_gold_spans(passage, ["exact figure", "sold the client position"])
    assert runs == [[3, 4], [7, 8, 9, 10]]
    # the two runs are genuinely non-contiguous
    assert max(runs[0]) + 1 < min(runs[1])


def test_find_gold_spans_missing_phrase_yields_empty_run():
    runs = find_gold_spans("a b c d", ["b c", "x y"])
    assert runs == [[1, 2], []]


# ---------------------------------------------------------------- grade_passage_attempt


def _spans_for(passage, phrases):
    return find_gold_spans(passage, phrases)


def test_passage_attempt_fully_correct():
    passage = "He traded on the tip and told his friend to buy."
    spans = _spans_for(passage, ["traded on the tip", "told his friend to buy"])
    sel = [i for run in spans for i in run]
    res = grade_passage_attempt(PassageAttempt(UNETHICAL, UNETHICAL, sel, spans))
    assert res["correct"] is True and res["highlight"] == "correct"


def test_passage_attempt_wrong_verdict_not_fully_correct():
    passage = "He traded on the tip and told his friend to buy."
    spans = _spans_for(passage, ["traded on the tip", "told his friend to buy"])
    sel = [i for run in spans for i in run]
    res = grade_passage_attempt(PassageAttempt(ETHICAL, UNETHICAL, sel, spans))
    assert res["verdict_correct"] is False and res["correct"] is False


def test_passage_attempt_partial_highlight_not_fully_correct():
    passage = "He traded on the tip and told his friend to buy."
    spans = _spans_for(passage, ["traded on the tip", "told his friend to buy"])
    res = grade_passage_attempt(PassageAttempt(UNETHICAL, UNETHICAL, spans[0], spans))
    assert res["highlight"] == "partial" and res["correct"] is False


# ------------------------------------------------------------- the 30-passage bank


def _load_raw():
    out = []
    with open(PASSAGES, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def test_bank_loads_and_validates():
    passages = P.load_passages(PASSAGES)
    assert len(passages) == 30


def test_bank_is_balanced_and_multi_span():
    rows = _load_raw()
    verdicts = [r["verdict"] for r in rows]
    assert verdicts.count("ethical") == 15 and verdicts.count("unethical") == 15
    # F1's whole point: real multi-span coverage, not a single decisive phrase.
    assert all(len(r["gold_spans"]) >= 1 for r in rows)
    assert sum(1 for r in rows if len(r["gold_spans"]) >= 2) >= 25


def test_every_bank_item_perfect_selection_grades_correct():
    for r in _load_raw():
        phrases = [g["phrase"] for g in r["gold_spans"]]
        runs = find_gold_spans(r["passage"], phrases)
        assert all(runs), f"{r['item_id']}: a phrase is not token-locatable"
        perfect = [i for run in runs for i in run]
        assert grade_spans(perfect, runs)["grade"] == "correct", r["item_id"]


def test_every_bank_item_verdict_only_is_not_fully_correct():
    # Getting the verdict right but highlighting nothing must never grade fully correct.
    for r in _load_raw():
        phrases = [g["phrase"] for g in r["gold_spans"]]
        runs = find_gold_spans(r["passage"], phrases)
        res = grade_passage_attempt(
            PassageAttempt(r["verdict"], r["verdict"], [], runs)
        )
        assert res["correct"] is False, r["item_id"]


# --------------------------------------------------- schema validation (pure, no anki)


def _base_rec():
    return {
        "item_id": "X-01",
        "cluster": "c",
        "standard": "I(C)",
        "los_tags": ["los::ethics::x"],
        "verdict": "unethical",
        "passage": "He bought his own account first thing today before the clients.",
        "gold_spans": [
            {"phrase": "bought his own account first", "rationale": "trades ahead"},
            {"phrase": "before the clients", "rationale": "subordinates clients"},
        ],
        "rationale": "r",
    }


def _write(tmp, rec):
    path = os.path.join(tmp, "x.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    return path


def test_validator_accepts_valid_record(tmp_path):
    got = P.load_passages(_write(str(tmp_path), _base_rec()))
    assert got[0]["item_id"] == "X-01"


def test_validator_rejects_bad_verdict(tmp_path):
    rec = _base_rec()
    rec["verdict"] = "maybe"
    with pytest.raises(P.PassageValidationError):
        P.load_passages(_write(str(tmp_path), rec))


def test_validator_rejects_non_substring_phrase(tmp_path):
    rec = _base_rec()
    rec["gold_spans"][0]["phrase"] = "a phrase not present in the passage at all"
    with pytest.raises(P.PassageValidationError):
        P.load_passages(_write(str(tmp_path), rec))


def test_validator_rejects_empty_gold_spans(tmp_path):
    rec = _base_rec()
    rec["gold_spans"] = []
    with pytest.raises(P.PassageValidationError):
        P.load_passages(_write(str(tmp_path), rec))


def test_validator_rejects_overlapping_spans(tmp_path):
    rec = _base_rec()
    rec["gold_spans"] = [
        {"phrase": "bought his own account", "rationale": "a"},
        {"phrase": "his own account first", "rationale": "b"},  # overlaps the first
    ]
    with pytest.raises(P.PassageValidationError):
        P.load_passages(_write(str(tmp_path), rec))


def test_validator_rejects_missing_keys(tmp_path):
    rec = _base_rec()
    del rec["standard"]
    with pytest.raises(P.PassageValidationError):
        P.load_passages(_write(str(tmp_path), rec))


def test_validator_rejects_duplicate_item_id(tmp_path):
    rec = _base_rec()
    path = os.path.join(str(tmp_path), "x.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
        f.write(json.dumps(rec) + "\n")
    with pytest.raises(P.PassageValidationError):
        P.load_passages(path)


# ------------------------------------------------ importer round-trip (needs pylib)

try:
    import anki.collection as _anki_collection  # noqa: F401

    _HAVE_ANKI = True
except Exception:
    _HAVE_ANKI = False


@pytest.mark.skipif(
    not _HAVE_ANKI, reason="requires a built pylib (PYTHONPATH=out/pylib)"
)
def test_import_passages_roundtrip_idempotent(tmp_path):
    from anki.collection import Collection

    col = Collection(os.path.join(str(tmp_path), "c.anki2"))
    try:
        passages = P.load_passages(PASSAGES)
        stats1 = P.import_passages(col, passages)
        assert stats1["created"] == 30 and stats1["updated"] == 0
        # a note carries the passage + JSON answer key, tagged with cluster + los + one-passage
        nids = col.find_notes(f'note:"{P.NOTETYPE_NAME}"')
        assert len(nids) == 30
        note = col.get_note(nids[0])
        spans = json.loads(note["GoldSpans"])
        assert spans and all("phrase" in s and "rationale" in s for s in spans)
        assert note["Verdict"] in ("ethical", "unethical")
        assert any(t == "ethics::one-passage" for t in note.tags)
        # re-import updates in place rather than duplicating
        stats2 = P.import_passages(col, passages)
        assert stats2["created"] == 0 and stats2["updated"] == 30
        assert len(col.find_notes(f'note:"{P.NOTETYPE_NAME}"')) == 30
    finally:
        col.close()


# ---------------------------------------------------- shared-logic drift + JS parity

_MARKER_START = "CFA-SPAN-SHARED-START"
_MARKER_END = "CFA-SPAN-SHARED-END"


def _extract_shared(path):
    """Return the code strictly between the shared markers, indentation-normalized per line."""
    lines = open(path, encoding="utf-8").read().splitlines()
    start = end = None
    for i, ln in enumerate(lines):
        if _MARKER_START in ln and start is None:
            start = i
        elif _MARKER_END in ln and start is not None:
            end = i
            break
    assert start is not None and end is not None, f"markers not found in {path}"
    body = [ln.strip() for ln in lines[start + 1 : end]]
    return "\n".join(ln for ln in body if ln)


def test_shared_logic_block_matches_between_template_and_js():
    template_block = _extract_shared(FRONT)
    js_block = _extract_shared(JS_LOGIC)
    assert template_block, "empty shared block extracted from passage_front.html"
    assert template_block == js_block


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_python_js_multispan_agree():
    # (1) gold-span finding: every real passage (its authored phrases) + synthetic edge cases.
    span_cases = []
    for r in _load_raw():
        span_cases.append(
            {"passage": r["passage"], "phrases": [g["phrase"] for g in r["gold_spans"]]}
        )
    span_cases += [
        {
            "passage": "The Exact, FIGURE. of client's in-house team",
            "phrases": ["exact figure", "in-house team"],
        },
        {"passage": "a b c d e f", "phrases": ["b c", "e f"]},
        {"passage": "a b c", "phrases": ["x y", "b"]},
        {"passage": "one—two three four", "phrases": ["two three", ""]},
        {
            "passage": "clients' funds are pooled here",
            "phrases": ["clients funds", "pooled here"],
        },
    ]

    # (2) grading: a matrix of selections x gold-span sets x caps (defaults + explicit).
    grade_cases = []
    gold_sets = [
        [[1, 2], [5, 6]],
        [[3, 4, 5]],
        [[0], [2], [4]],
        [[7, 8], [10, 11, 12]],
        [[1, 2], []],  # a missing span (empty run)
    ]
    for gold in gold_sets:
        flat = [i for run in gold for i in run]
        hi = max(flat) if flat else 0
        selections = [
            flat,
            (gold[0] if gold else []),
            list(range(0, hi + 14)),
            [100, 101, 102],
            flat[:-1] if len(flat) > 1 else [999],
            [],
            list(reversed(flat)),
        ]
        for sel in selections:
            for cap in (None, 6, 12, len(flat)):
                grade_cases.append({"selection": sel, "gold_spans": gold, "cap": cap})

    payload = {"spans": span_cases, "grade": grade_cases}
    with tempfile.TemporaryDirectory() as d:
        inp = os.path.join(d, "in.json")
        with open(inp, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        proc = subprocess.run(
            [NODE, JS_RUNNER, inp],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(JS_RUNNER),
            check=False,
        )
    assert proc.returncode == 0, proc.stderr
    js = json.loads(proc.stdout)

    py_spans = [find_gold_spans(c["passage"], c["phrases"]) for c in span_cases]
    py_grade = [
        grade_spans(c["selection"], c["gold_spans"], c["cap"]) for c in grade_cases
    ]
    py_grade_tolerant = [
        grade_spans_tolerant(c["selection"], c["gold_spans"], c["cap"])
        for c in grade_cases
    ]

    assert js["spans"] == py_spans
    # Compare the full grade dicts (grade, found, total, per_span, width_ok, cap) structurally.
    assert js["grade"] == py_grade
    # Item 2: the tolerant grader (grade, found, near, matched, total, per_span, ...) must agree too,
    # so mobile's partial-credit grade is byte-identical to the desktop card's shared JS.
    assert js["grade_tolerant"] == py_grade_tolerant
    assert len(py_grade) == len(grade_cases) and len(py_spans) == len(span_cases)
