# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""A1 tests — AI-vs-baseline comparison.

No ``anki`` dependency and no network: the LLM is injected via ``complete_fn``.
Covers the TF-IDF baseline grader, the AI-off honest report (LLM assertion
skipped), and the gate that the AI must *beat both* baselines when it runs.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(EVAL))
sys.path.insert(0, os.path.join(REPO, "cfa", "ethics_pairs"))
sys.path.insert(0, EVAL)
sys.path.insert(0, REPO)

import baseline_compare as B  # noqa: E402


def _off_client(**kwargs):
    # AI OFF: grade_semantic falls back to the deterministic grade.
    return {"ok": False, "text": "", "model": "gpt-4o-mini", "usage": {},
            "error": "no_api_key", "purpose": kwargs.get("purpose", "")}


def _oracle(grade_for_item):
    """Build a complete_fn that returns a chosen human-ish grade per passage."""
    passages = {r["item_id"]: r for r in B.E._load(B.E.PASSAGES)}
    attempts = {r["item_id"]: r for r in B.E._load(B.E.ATTEMPTS)}

    def fn(**kwargs):
        user = kwargs["user"]
        grade = "wrong"
        for a in attempts.values():
            if passages[a["item_id"]]["passage"] in user:
                grade = grade_for_item(a)
                break
        payload = {"highlight_grade": grade, "explanation": "oracle", "spans": []}
        return {"ok": True, "model": "gpt-4o-mini", "usage": {"total_tokens": 10},
                "error": None, "purpose": kwargs.get("purpose", ""),
                "text": json.dumps(payload)}

    return fn


def test_tfidf_grade_full_partial_none():
    passage = (
        "She learned the exact unreleased quarterly earnings figure and "
        "sells the company."
    )
    gold = [{"phrase": "exact unreleased quarterly earnings figure"},
            {"phrase": "sells the company"}]
    # both spans highlighted -> correct
    full = B.tfidf_grade(passage, gold, ["exact unreleased quarterly earnings figure",
                                         "sells the company"])
    assert full["grade"] == "correct" and full["covered"] == 2
    # one span highlighted -> somewhat (half covered)
    half = B.tfidf_grade(passage, gold, ["sells the company"])
    assert half["grade"] == "somewhat" and half["covered"] == 1
    # nothing relevant highlighted -> wrong
    none = B.tfidf_grade(passage, gold, ["completely unrelated words here"])
    assert none["grade"] == "wrong" and none["covered"] == 0


def test_tfidf_grade_empty_gold_is_wrong():
    assert B.tfidf_grade("some passage", [], ["anything"])["grade"] == "wrong"


def test_compare_ai_off_reports_both_baselines_and_skips_llm():
    report = B.run_compare(complete_fn=_off_client)
    assert report["n"] == 30
    assert report["ran_ai"] is False
    # deterministic-span baseline is the frozen shipped AI-off number
    assert abs(report["deterministic_agreement"] - 0.7333) < 0.01
    # the simpler TF-IDF baseline produces a real number in range
    assert 0.0 <= report["tfidf_agreement"] <= 1.0
    text = B.format_report(report)
    assert "SKIPPED" in text and "AI OFF" in text


def test_ai_beats_baseline_gate_passes_with_oracle():
    # An oracle that returns the human grade -> perfect agreement, which must
    # beat both baselines (each < 1.0).
    report = B.run_compare(complete_fn=_oracle(lambda a: a["human_grade"]))
    assert report["ran_ai"] is True
    best_baseline = max(report["deterministic_agreement"], report["tfidf_agreement"])
    assert report["llm_agreement"] > best_baseline


def test_ai_that_loses_to_baseline_fails_the_gate(monkeypatch):
    # A useless LLM (always "wrong") cannot beat the baselines: run_compare
    # reports it honestly and main() exits non-zero (the gate rejects it).
    losing = B.run_compare(complete_fn=_oracle(lambda a: "wrong"))
    best_baseline = max(losing["deterministic_agreement"], losing["tfidf_agreement"])
    assert losing["ran_ai"] is True
    assert losing["llm_agreement"] <= best_baseline
    monkeypatch.setattr(B, "run_compare", lambda complete_fn=None: losing)
    assert B.main([]) == 1


def test_main_ai_off_returns_zero():
    # AI-off run must never fail the process (nothing to hold to the bar).
    assert B.main([]) == 0
