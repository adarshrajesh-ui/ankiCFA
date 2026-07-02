# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Tests for the in-vignette highlight interaction: tokenization, span-overlap grading, the data
bank's gold phrases, and a Python<->JS agreement cross-check so the same grades are produced in the
card template (desktop Anki + AnkiDroid webviews) as in the pure Python scorer.

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

import import_pairs  # noqa: E402
from ethics_scoring import (  # noqa: E402
    CONFORM,
    HIGHLIGHT_CAP_SLACK,
    VIOLATE,
    PairAttempt,
    default_cap,
    find_gold_indices,
    grade_attempt,
    grade_highlight,
    normalized_tokens,
    tokenize,
)

FRONT = os.path.join(PKG, "templates", "front.html")
PAIRS = os.path.join(PKG, "pairs.jsonl")
JS_LOGIC = os.path.join(HERE, "js", "highlight_logic.js")
JS_RUNNER = os.path.join(HERE, "js", "run_matrix.js")
NODE = shutil.which("node")


# --------------------------------------------------------------- grade_highlight tiers


def test_selection_equal_to_gold_is_correct():
    assert grade_highlight([3, 4, 5], [3, 4, 5]) == "correct"


def test_small_superset_containing_gold_is_correct():
    # default cap = len(gold) + slack = 3 + 5 = 8; a 5-word span is comfortably within it.
    assert grade_highlight([2, 3, 4, 5, 6], [3, 4, 5]) == "correct"


def test_selection_exactly_at_cap_is_correct():
    gold = [3, 4, 5]
    cap = default_cap(len(gold))
    sel = list(range(0, cap))  # cap words, contains gold
    assert len(sel) == cap
    assert grade_highlight(sel, gold) == "correct"


def test_one_word_over_cap_is_somewhat():
    gold = [3, 4, 5]
    sel = list(range(0, default_cap(len(gold)) + 1))
    assert grade_highlight(sel, gold) == "somewhat"


def test_large_superset_containing_gold_is_somewhat():
    assert grade_highlight(list(range(0, 20)), [3, 4, 5]) == "somewhat"


def test_disjoint_selection_is_wrong():
    assert grade_highlight([10, 11, 12], [3, 4, 5]) == "wrong"


def test_partial_overlap_missing_a_gold_word_is_wrong():
    # contains 3 and 4 but not 5 -> missing a gold word -> wrong
    assert grade_highlight([2, 3, 4], [3, 4, 5]) == "wrong"


def test_empty_selection_is_wrong():
    assert grade_highlight([], [3, 4, 5]) == "wrong"


def test_custom_cap_overrides_default():
    gold = [3, 4, 5]
    assert grade_highlight([1, 2, 3, 4, 5], gold, cap=5) == "correct"  # 5 <= 5
    assert grade_highlight([0, 1, 2, 3, 4, 5], gold, cap=5) == "somewhat"  # 6 > 5


def test_unordered_selection_is_handled():
    assert grade_highlight([5, 3, 4], [3, 4, 5]) == "correct"


def test_cap_slack_constant_is_the_single_tunable():
    assert HIGHLIGHT_CAP_SLACK == 5
    assert default_cap(3) == 3 + HIGHLIGHT_CAP_SLACK


# --------------------------------------------------------------------- tokenization


def test_tokenize_splits_on_any_whitespace_run():
    assert tokenize("  a  b\tc\n d ") == ["a", "b", "c", "d"]
    assert tokenize("") == []
    assert tokenize(None) == []


def test_normalized_tokens_strip_surrounding_punct_and_lowercase():
    assert normalized_tokens("The Exact, FIGURE.") == ["the", "exact", "figure"]


def test_normalized_tokens_keep_interior_punctuation():
    assert normalized_tokens("client's in-house still-secret") == [
        "client's",
        "in-house",
        "still-secret",
    ]
    # a trailing apostrophe (possessive plural) is surrounding punctuation -> stripped
    assert normalized_tokens("clients'") == ["clients"]


def test_find_gold_indices_basic_and_punctuation_tolerant():
    v = "who tells her the exact unreleased figure, which is far"
    assert find_gold_indices(v, "exact unreleased figure") == [4, 5, 6]


def test_find_gold_indices_not_found_or_empty():
    assert find_gold_indices("a b c", "x y") == []
    assert find_gold_indices("a b c", "") == []


# ------------------------------------------------------------------ grade_attempt


def _attempt(
    judged_a, judged_b, *, selection_case="A", selection=(3, 4, 5), gold=(3, 4, 5)
):
    return PairAttempt(
        judged_a=judged_a,
        judged_b=judged_b,
        answer_a=VIOLATE,
        answer_b=CONFORM,
        selection_case=selection_case,
        selection_indices=selection,
        decisive_case="A",
        gold_indices=gold,
    )


def test_grade_attempt_fully_correct():
    res = grade_attempt(_attempt(VIOLATE, CONFORM))
    assert res["correct"] is True and res["highlight"] == "correct"


def test_grade_attempt_somewhat_not_fully_correct():
    res = grade_attempt(_attempt(VIOLATE, CONFORM, selection=tuple(range(0, 20))))
    assert res["highlight"] == "somewhat" and res["correct"] is False


def test_grade_attempt_wrong_case_not_fully_correct():
    res = grade_attempt(_attempt(VIOLATE, CONFORM, selection_case="B"))
    assert res["highlight"] == "wrong" and res["correct"] is False


# --------------------------------------------------------------- the 30-pair bank


def _load_raw_pairs():
    pairs = []
    with open(PAIRS, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                pairs.append(json.loads(line))
    return pairs


def test_all_30_pairs_have_verbatim_locatable_contiguous_gold():
    pairs = _load_raw_pairs()
    assert len(pairs) == 30
    for p in pairs:
        pid = p["pair_id"]
        case = p["decisive_phrase_case"]
        phrase = p["decisive_phrase"]
        vign = p["vignette_a"] if case == "A" else p["vignette_b"]
        assert phrase in vign, f"{pid}: not a verbatim substring"
        idx = find_gold_indices(vign, phrase)
        assert idx, f"{pid}: not token-locatable"
        assert len(idx) == len(tokenize(phrase)), f"{pid}: token count mismatch"
        assert idx == list(range(idx[0], idx[0] + len(idx))), f"{pid}: not contiguous"
        # the decisive phrase must live in the VIOLATING vignette
        violate_case = "A" if p["answer_a"] == "violate" else "B"
        assert case == violate_case, f"{pid}: phrase case is not the violating vignette"


# --------------------------------------------------- importer bank validation (pure)


def _base_rec():
    return {
        "pair_id": "X-01",
        "cluster": "c",
        "cluster_label": "C",
        "los_tags": ["los::ethics::x"],
        "vignette_a": "He bought his own account first thing today.",
        "answer_a": "violate",
        "vignette_b": "He filled the client first then bought.",
        "answer_b": "conform",
        "decisive_fact": "d",
        "decisive_phrase": "his own account first",
        "decisive_phrase_case": "A",
        "distractors": ["1", "2", "3"],
        "rationale": "r",
        "standard": "I(C)",
    }


def _write_rec(tmp, rec):
    path = os.path.join(tmp, "x.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    return path


def test_load_pairs_accepts_valid_phrase(tmp_path):
    pairs = import_pairs.load_pairs(_write_rec(str(tmp_path), _base_rec()))
    assert pairs[0]["decisive_phrase"] == "his own account first"


def test_load_pairs_rejects_non_substring_phrase(tmp_path):
    rec = _base_rec()
    rec["decisive_phrase"] = "phrase absent from the vignette"
    with pytest.raises(ValueError):
        import_pairs.load_pairs(_write_rec(str(tmp_path), rec))


def test_load_pairs_rejects_phrase_in_non_violating_case(tmp_path):
    rec = _base_rec()
    rec["decisive_phrase_case"] = "B"  # B is the conforming vignette here
    with pytest.raises(ValueError):
        import_pairs.load_pairs(_write_rec(str(tmp_path), rec))


# ---------------------------------------------------- shared-logic drift + JS parity

_MARKER_START = "CFA-HIGHLIGHT-SHARED-START"
_MARKER_END = "CFA-HIGHLIGHT-SHARED-END"


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
    assert template_block, "empty shared block extracted from front.html"
    assert template_block == js_block


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_python_js_tokenization_and_grading_agree():
    # (1) gold-finding: every real pair + synthetic edge cases (punctuation, dashes, misses).
    gold_cases = []
    for p in _load_raw_pairs():
        case = p["decisive_phrase_case"]
        vign = p["vignette_a"] if case == "A" else p["vignette_b"]
        gold_cases.append({"vignette": vign, "gold": p["decisive_phrase"]})
    gold_cases += [
        {
            "vignette": "The Exact, FIGURE. of client's in-house team",
            "gold": "exact figure",
        },
        {"vignette": "a b c d e", "gold": "c d"},
        {"vignette": "a b c", "gold": "x y"},
        {"vignette": "a b c", "gold": ""},
        {"vignette": "one\u2014two three", "gold": "two three"},
        {"vignette": "clients' funds are pooled", "gold": "clients funds"},
    ]

    # (2) grading: a matrix of selections x gold spans x caps (including defaults + explicit).
    grade_cases = []
    for gold in ([3, 4, 5], [0], [0, 1], [7, 8, 9, 10]):
        n = gold[-1] if gold else 0
        selections = [
            gold,
            [gold[0] - 1] + gold + [gold[-1] + 1]
            if gold[0] > 0
            else gold + [gold[-1] + 1],
            list(range(0, n + 12)),
            [100, 101, 102],
            gold[:-1] if len(gold) > 1 else [999],
            [],
            list(reversed(gold)),
        ]
        for sel in selections:
            for cap in (None, 5, 8, len(gold)):
                grade_cases.append({"selection": sel, "gold": gold, "cap": cap})

    payload = {"gold": gold_cases, "grade": grade_cases}
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

    py_gold = [find_gold_indices(c["vignette"], c["gold"]) for c in gold_cases]
    py_grade = [
        grade_highlight(c["selection"], c["gold"], c["cap"]) for c in grade_cases
    ]

    assert js["gold"] == py_gold
    assert js["grade"] == py_grade
    assert len(py_grade) == len(grade_cases) and len(py_gold) == len(gold_cases)
