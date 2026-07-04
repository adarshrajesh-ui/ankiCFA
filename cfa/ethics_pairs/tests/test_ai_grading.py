# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Tests for F2 semantic AI grading of ethics highlights.

No ``anki`` dependency and no network: the LLM is injected via ``complete_fn``.
Covers the AI-off fallback contract, the semantic-override path, robust parsing,
the never-leak-the-key/always-include-the-evidence prompt, and the 30-item
human-labeled eval both AI-off (deterministic) and with a mocked oracle LLM.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(PKG))
sys.path.insert(0, PKG)
sys.path.insert(0, REPO)

import ai_grading as A  # noqa: E402
import eval_ai_grading as E  # noqa: E402

PASSAGE = (
    "Priya, a buy-side analyst, spends the week assembling public filings and "
    "industry shipment data, then calls a former plant employee who tells her "
    "the exact unreleased quarterly earnings figure, which is far below "
    "guidance. Combining everything, she concludes earnings will disappoint and "
    "sells the company out of her clients' portfolios."
)
GOLD = [
    {"phrase": "exact unreleased quarterly earnings figure", "rationale": "MNPI"},
    {
        "phrase": "sells the company out of her clients' portfolios",
        "rationale": "trades on it",
    },
]


def _off_client(**kwargs):
    return {
        "ok": False,
        "text": "",
        "model": "gpt-4o-mini",
        "usage": {},
        "error": "no_api_key",
        "purpose": kwargs.get("purpose", ""),
    }


def _oracle_client(text):
    calls = {}

    def fn(**kwargs):
        calls.update(kwargs)
        fn.last = kwargs
        return {
            "ok": True,
            "text": text,
            "model": "gpt-4o-mini",
            "usage": {"total_tokens": 100},
            "error": None,
            "purpose": kwargs.get("purpose", ""),
        }

    fn.last = None
    return fn


# ---------------------------------------------------------------- AI-off fallback


def test_ai_off_falls_back_to_deterministic_and_matches():
    # exact gold selection -> deterministic "correct"
    res = A.grade_semantic(
        PASSAGE,
        "unethical",
        "unethical",
        GOLD,
        [g["phrase"] for g in GOLD],
        complete_fn=_off_client,
    )
    assert res["source"] == "fallback" and res["ok"] is False
    assert res["grade"] == "correct" and res["correct"] is True
    assert res["error"] == "no_api_key"


def test_ai_off_partial_selection_is_partial():
    res = A.grade_semantic(
        PASSAGE,
        "unethical",
        "unethical",
        GOLD,
        ["exact unreleased quarterly earnings figure"],
        complete_fn=_off_client,
    )
    assert res["source"] == "fallback"
    assert res["grade"] == "partial" and res["correct"] is False
    assert res["per_span"][0]["matched"] is True
    assert res["per_span"][1]["matched"] is False


def test_ai_off_wrong_verdict_never_correct():
    res = A.grade_semantic(
        PASSAGE,
        "unethical",
        "ethical",
        GOLD,
        [g["phrase"] for g in GOLD],
        complete_fn=_off_client,
    )
    assert res["verdict_correct"] is False and res["correct"] is False


# ------------------------------------------------------- INC2: provenance (standard + item_id)


def test_fallback_carries_item_id_and_standard():
    # AI-off fallback must still echo the provenance the card supplied, so the UI can name the
    # governing Standard even without AI. (Before INC2 these keys did not exist in the result.)
    res = A.grade_semantic(
        PASSAGE,
        "unethical",
        "unethical",
        GOLD,
        [g["phrase"] for g in GOLD],
        complete_fn=_off_client,
        item_id="SMD-01",
        standard="II(A) Material Nonpublic Information",
    )
    assert res["source"] == "fallback"
    assert res["item_id"] == "SMD-01"
    assert res["standard"] == "II(A) Material Nonpublic Information"


def test_ai_path_carries_item_id_and_standard():
    oracle = _oracle_client(
        json.dumps({"highlight_grade": "correct", "explanation": "ok", "spans": []})
    )
    res = A.grade_semantic(
        PASSAGE,
        "unethical",
        "unethical",
        GOLD,
        [g["phrase"] for g in GOLD],
        complete_fn=oracle,
        item_id="SMD-01",
        standard="II(A) Material Nonpublic Information",
    )
    assert res["source"] == "ai"
    assert res["item_id"] == "SMD-01"
    assert res["standard"] == "II(A) Material Nonpublic Information"


def test_provenance_defaults_are_empty_strings_not_missing():
    # When the card supplies no provenance, the keys are present but empty (stable schema).
    res = A.grade_semantic(
        PASSAGE, "unethical", "unethical", GOLD, [], complete_fn=_off_client
    )
    assert res["item_id"] == "" and res["standard"] == ""


def test_standard_never_leaks_into_prompt_but_flows_to_result():
    # The provenance Standard is result-only metadata; it must NOT be injected into the LLM prompt.
    oracle = _oracle_client(json.dumps({"highlight_grade": "correct", "spans": []}))
    res = A.grade_semantic(
        PASSAGE,
        "unethical",
        "unethical",
        GOLD,
        ["sells the company"],
        complete_fn=oracle,
        item_id="SMD-01",
        standard="II(A) Material Nonpublic Information",
    )
    blob = oracle.last["system"] + "\n" + oracle.last["user"]
    assert "II(A) Material Nonpublic Information" not in blob
    assert res["standard"] == "II(A) Material Nonpublic Information"


# ---------------------------------------------------------------- semantic path


def test_ai_semantic_override_upgrades_partial_to_correct():
    # learner clipped the boundaries -> deterministic would say partial/wrong,
    # but the oracle LLM recognizes the right evidence and says correct.
    oracle = _oracle_client(
        json.dumps(
            {
                "verdict_correct": True,
                "highlight_grade": "correct",
                "explanation": "Both the MNPI and the trade were identified.",
                "spans": [
                    {
                        "phrase": GOLD[0]["phrase"],
                        "matched": True,
                        "note": "the earnings figure",
                    },
                    {"phrase": GOLD[1]["phrase"], "matched": True, "note": "the sale"},
                ],
            }
        )
    )
    res = A.grade_semantic(
        PASSAGE,
        "unethical",
        "unethical",
        GOLD,
        ["unreleased quarterly earnings figure", "sells the company"],
        complete_fn=oracle,
    )
    assert res["source"] == "ai" and res["ok"] is True
    assert res["grade"] == "correct" and res["correct"] is True
    assert "identified" in res["explanation"].lower()
    assert all(s["matched"] for s in res["per_span"])


def test_ai_verdict_correctness_is_computed_not_trusted():
    # Even if the model claims verdict_correct True, a wrong verdict stays wrong.
    oracle = _oracle_client(
        json.dumps(
            {
                "verdict_correct": True,
                "highlight_grade": "correct",
                "explanation": "x",
                "spans": [],
            }
        )
    )
    res = A.grade_semantic(
        PASSAGE, "unethical", "ethical", GOLD, [], complete_fn=oracle
    )
    assert res["verdict_correct"] is False and res["correct"] is False


def test_ai_grade_string_is_sanitized():
    oracle = _oracle_client(
        json.dumps(
            {
                "highlight_grade": "PERFECT",
                "explanation": "",
                "spans": [],
            }
        )
    )
    res = A.grade_semantic(
        PASSAGE, "unethical", "unethical", GOLD, [], complete_fn=oracle
    )
    # unknown grade -> defaults to "wrong", never crashes
    assert res["grade"] == "wrong"


# ---------------------------------------------------------------- robust parsing


def test_code_fenced_json_parses():
    oracle = _oracle_client(
        '```json\n{"highlight_grade": "somewhat", "explanation": "e", "spans": []}\n```'
    )
    res = A.grade_semantic(
        PASSAGE, "unethical", "unethical", GOLD, [], complete_fn=oracle
    )
    assert res["source"] == "ai" and res["grade"] == "somewhat"


def test_json_with_leading_prose_parses():
    oracle = _oracle_client(
        'Here is my grade: {"highlight_grade": "partial", "explanation": "e", "spans": []} done'
    )
    res = A.grade_semantic(
        PASSAGE, "unethical", "unethical", GOLD, [], complete_fn=oracle
    )
    assert res["grade"] == "partial"


def test_unparseable_response_falls_back():
    oracle = _oracle_client("I think this is basically correct, nice work!")
    res = A.grade_semantic(
        PASSAGE,
        "unethical",
        "unethical",
        GOLD,
        [g["phrase"] for g in GOLD],
        complete_fn=oracle,
    )
    assert res["source"] == "fallback" and res["error"] == "unparseable_response"
    # fallback still produces the deterministic grade
    assert res["grade"] == "correct"


def test_grade_semantic_handles_none_result():
    # A broken shim returning None must be treated as AI-off, not crash.
    res = A.grade_semantic(
        PASSAGE, "unethical", "unethical", GOLD, [], complete_fn=lambda **k: None
    )
    assert res["source"] == "fallback"


# ------------------------------------------------------------------- prompt hygiene


def test_prompt_includes_evidence_and_never_the_key():
    oracle = _oracle_client(json.dumps({"highlight_grade": "correct", "spans": []}))
    os.environ["OPENAI_API_KEY"] = "sk-should-never-appear-in-prompt"
    try:
        A.grade_semantic(
            PASSAGE,
            "unethical",
            "unethical",
            GOLD,
            ["sells the company"],
            complete_fn=oracle,
        )
    finally:
        del os.environ["OPENAI_API_KEY"]
    sent = oracle.last
    blob = sent["system"] + "\n" + sent["user"]
    assert "sk-should-never-appear-in-prompt" not in blob
    assert PASSAGE in sent["user"]
    assert "unethical" in sent["user"]
    assert GOLD[0]["phrase"] in sent["user"]
    assert "sells the company" in sent["user"]  # the learner's span
    assert sent["purpose"] == "grade_ethics_highlight"


# ------------------------------------------------------------------- eval harness


def test_eval_runs_ai_off_and_reports_baseline():
    report = E.run_eval(complete_fn=_off_client)
    assert report["n"] == 30
    assert report["ran_ai"] is False
    # deterministic fallback: the frozen baseline we authored
    assert abs(report["grade_agreement"] - 0.7333) < 0.01
    assert report["grade_agreement"] == report["deterministic_baseline_agreement"]


def test_eval_with_oracle_llm_hits_threshold():
    # An oracle that always returns the human grade -> perfect agreement,
    # proving the harness measures and asserts LLM agreement correctly.
    passages = {r["item_id"]: r for r in E._load(E.PASSAGES)}
    attempts = {r["item_id"]: r for r in E._load(E.ATTEMPTS)}

    def oracle(**kwargs):
        # recover which item by matching the passage text in the prompt
        user = kwargs["user"]
        human = "wrong"
        for a in attempts.values():
            p = passages[a["item_id"]]
            if p["passage"] in user:
                human = a["human_grade"]
                break
        return {
            "ok": True,
            "model": "gpt-4o-mini",
            "usage": {"total_tokens": 10},
            "error": None,
            "purpose": kwargs.get("purpose", ""),
            "text": json.dumps(
                {"highlight_grade": human, "explanation": "oracle", "spans": []}
            ),
        }

    report = E.run_eval(complete_fn=oracle)
    assert report["ran_ai"] is True
    assert report["grade_agreement"] >= 0.8
    assert report["grade_agreement"] > report["deterministic_baseline_agreement"]
