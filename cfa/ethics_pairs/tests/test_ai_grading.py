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


def test_standard_is_supplied_to_prompt_and_flows_to_result():
    # The governing Standard is not secret; supplying it lets the AI cite the
    # authored Standard reliably instead of guessing from the vignette alone.
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
    assert "GOVERNING STANDARD SUPPLIED BY CARD" in blob
    assert "II(A) Material Nonpublic Information" in blob
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


def test_ai_correct_with_missing_span_flags_does_not_contradict_grade():
    # Live models sometimes return a valid overall grade while omitting or
    # under-filling `spans`. The UI must not show "Correct" and then mark every
    # gold span as missed.
    oracle = _oracle_client(
        json.dumps(
            {
                "highlight_grade": "correct",
                "explanation": "Both pieces of evidence were covered.",
                "spans": [],
            }
        )
    )
    res = A.grade_semantic(
        PASSAGE,
        "unethical",
        "unethical",
        GOLD,
        [g["phrase"] for g in GOLD],
        complete_fn=oracle,
    )
    assert res["grade"] == "correct"
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
    assert sent["temperature"] == 0.25
    assert sent["max_tokens"] == 650


def test_prompt_includes_structured_highlights_and_coverage():
    oracle = _oracle_client(
        json.dumps(
            {
                "highlight_grade": "somewhat",
                "learner_intent": "They noticed the earnings figure and the trade.",
                "evidence_precision": "overbroad",
                "needed_evidence": [g["phrase"] for g in GOLD],
                "explanation": "Covered the right facts but with extra context.",
                "spans": [],
            }
        )
    )
    res = A.grade_semantic(
        PASSAGE,
        "unethical",
        "unethical",
        GOLD,
        ["the exact unreleased quarterly earnings figure", "sells the company"],
        selection_indices=list(range(0, 20)),
        learner_highlights=[
            {"text": "the exact unreleased quarterly earnings figure", "lo": 15, "hi": 20},
            {"text": "sells the company", "lo": 30, "hi": 32},
        ],
        complete_fn=oracle,
    )
    prompt = oracle.last["user"]
    assert '"the exact unreleased quarterly earnings figure" (token range 15-20)' in prompt
    assert "HIGHLIGHT COVERAGE: 20 of" in prompt
    assert "Use this to judge precision/overbreadth" in prompt
    assert res["evidence_precision"] == "overbroad"
    assert "earnings figure" in res["learner_intent"]
    assert res["needed_evidence"] == [g["phrase"] for g in GOLD]


def test_fallback_marks_whole_paragraph_as_overbroad():
    res = A.grade_fallback(
        PASSAGE,
        "unethical",
        "unethical",
        GOLD,
        [PASSAGE],
        selection_indices=list(range(len(PASSAGE.split()))),
    )
    assert res["grade"] == "somewhat"
    assert res["evidence_precision"] == "overbroad"
    assert res["correct"] is False


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


# --- richer, tailored feedback (coaching + study tip) ------------------------


def _rich_complete(**_):
    return {
        "ok": True,
        "model": "gpt-4o-mini",
        "error": None,
        "text": (
            '{"verdict_correct": true, "highlight_grade": "partial", "confidence": 0.8,'
            ' "standard": "II(A) Material Nonpublic Information",'
            ' "explanation": "missed the trading phrase",'
            ' "coaching": "Your unethical call is right; highlight the trade-before-public phrase.",'
            ' "study_tip": "Drill spotting the ACT of trading on MNPI.",'
            ' "spans": [{"phrase": "x", "matched": false, "note": "the MNPI"}]}'
        ),
    }


def test_ai_result_carries_tailored_coaching_and_tip():
    r = A.grade_semantic(
        "passage", "unethical", "unethical",
        [{"phrase": "x", "rationale": "MNPI"}], ["x"],
        complete_fn=_rich_complete,
    )
    assert r["source"] == "ai"
    assert "highlight" in r["coaching"].lower() or "unethical" in r["coaching"].lower()
    assert r["study_tip"]
    assert r["confidence"] == 0.8
    assert r["standard"] == "II(A) Material Nonpublic Information"


def test_fallback_coaching_nudges_to_ai():
    r = A.grade_fallback(
        "passage", "unethical", "unethical",
        [{"phrase": "x", "rationale": "MNPI"}], ["x"],
        standard="II(A)",
    )
    assert r["source"] == "fallback"
    assert "AI grading" in r["coaching"]  # explicitly points to the AI upgrade
    assert "study_tip" in r


# --- A2 wrong-answer-rate gate ----------------------------------------------


def test_wrong_answer_rate_reported_and_zero_under_ai_off():
    # The deterministic fallback never false-accepts a human-incorrect answer,
    # so the safety metric is 0.0 over the 5 human-incorrect gold attempts.
    report = E.run_eval(complete_fn=_off_client)
    assert report["human_incorrect"] == 5
    assert report["false_accepts"] == 0
    assert report["wrong_answer_rate"] == 0.0
    # cutoffs are surfaced in the report so evidence carries them
    assert report["accuracy_cut"] == E.ACCURACY_CUT
    assert report["wrong_answer_rate_cut"] == E.WRONG_ANSWER_RATE_CUT


def test_ai_off_never_fails_process_even_below_accuracy_cut(monkeypatch):
    # AI-off accuracy (0.733) is below ACCURACY_CUT, but the AI-off contract
    # means the process must still succeed and score honestly.
    assert E.ACCURACY_CUT > 0.733  # precondition: the cut is above the fallback
    os.environ.pop("OPENAI_API_KEY", None)
    run_eval = E.run_eval
    monkeypatch.setattr(E, "run_eval", lambda: run_eval(complete_fn=_off_client))
    assert E.main([]) == 0


def _incorrect_item_ids():
    attempts = {r["item_id"]: r for r in E._load(E.ATTEMPTS)}
    return [a["item_id"] for a in attempts.values() if not a["human_correct"]]


def _oracle_by_passage(grade_for):
    """Build an oracle that returns grade_for(attempt) for the matched item."""
    passages = {r["item_id"]: r for r in E._load(E.PASSAGES)}
    attempts = {r["item_id"]: r for r in E._load(E.ATTEMPTS)}

    def oracle(**kwargs):
        user = kwargs["user"]
        chosen = "wrong"
        for a in attempts.values():
            if passages[a["item_id"]]["passage"] in user:
                chosen = grade_for(a)
                break
        return {
            "ok": True,
            "model": "gpt-4o-mini",
            "usage": {"total_tokens": 10},
            "error": None,
            "purpose": kwargs.get("purpose", ""),
            "text": json.dumps(
                {"highlight_grade": chosen, "explanation": "oracle", "spans": []}
            ),
        }

    return oracle


def test_oracle_llm_passes_named_gate():
    # An oracle returning the human grade -> perfect accuracy, zero false
    # accepts -> both gate legs PASS and main() exits 0.
    report = E.run_eval(complete_fn=_oracle_by_passage(lambda a: a["human_grade"]))
    assert report["ran_ai"] is True
    assert report["wrong_answer_rate"] == 0.0
    assert report["correct_accuracy"] >= E.ACCURACY_CUT
    assert report["gate_pass"] is True


def test_false_accepting_llm_trips_wrong_answer_gate():
    # A grader that calls every human-incorrect answer "correct" drives the
    # wrong-answer rate to 1.0 -> the safety leg FAILs and main() exits 1,
    # even though overall accuracy could look high.
    def grade_for(a):
        # keep correct items correct, but wrongly upgrade incorrect ones
        return "correct"

    oracle = _oracle_by_passage(grade_for)
    report = E.run_eval(complete_fn=oracle)
    assert report["ran_ai"] is True
    # 4 of the 5 human-incorrect attempts are eligible false-accepts; the 5th
    # has a wrong verdict the grader always rejects (verdict gate), so it can
    # never be false-accepted. Either way the safety rate blows past the cut.
    assert report["human_incorrect"] == 5
    assert report["false_accepts"] == 4
    assert report["wrong_answer_rate"] == 0.8
    assert report["wrong_answer_rate"] > report["wrong_answer_rate_cut"]
    assert report["gate_pass"] is False

    # verify main() surfaces the failure as a non-zero exit
    import contextlib
    import io

    def _patched_run(*_a, **_k):
        return report

    orig = E.run_eval
    E.run_eval = _patched_run
    try:
        os.environ["OPENAI_API_KEY"] = "sk-test"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = E.main([])
    finally:
        E.run_eval = orig
        os.environ.pop("OPENAI_API_KEY", None)
    assert rc == 1
    assert "wrong-answer rate" in buf.getvalue()


# --- per-highlight critique (per_learner_span) ------------------------------
#
# The rework's core ask: feedback must be TARGETED AT WHAT THE LEARNER ACTUALLY HIGHLIGHTED. For each
# learner highlight the grader must say whether it is decisive / excessive (too broad) / irrelevant /
# partial, quote the learner's own words, and (via the deterministic coverage numbers) ground that
# call. These tests lock the prompt guidance, the parse-through, and the stable AI-off derivation.

# Gold span 1 = tokens 24-28 ("exact unreleased quarterly earnings figure");
# gold span 2 = tokens 42-49 ("sells the company out of her clients' portfolios").
_FOUR_HIGHLIGHTS = [
    # decisive: exactly gold span 1
    {"text": "exact unreleased quarterly earnings figure", "lo": 24, "hi": 28},
    # excessive: gold span 1 buried in a much wider grab
    {
        "text": "the exact unreleased quarterly earnings figure, which is far below guidance.",
        "lo": 23,
        "hi": 33,
    },
    # irrelevant: background, overlaps no gold span
    {"text": "spends the week assembling public filings", "lo": 4, "hi": 9},
    # partial: only part of gold span 2
    {"text": "sells the company", "lo": 42, "hi": 44},
]


def _four_highlight_selection():
    sel = []
    for h in _FOUR_HIGHLIGHTS:
        sel += list(range(h["lo"], h["hi"] + 1))
    return sel


def test_prompt_requires_per_highlight_critique_and_word_coverage_guidance():
    oracle = _oracle_client(json.dumps({"highlight_grade": "somewhat", "spans": []}))
    A.grade_semantic(
        PASSAGE,
        "unethical",
        "unethical",
        GOLD,
        [h["text"] for h in _FOUR_HIGHLIGHTS],
        selection_indices=_four_highlight_selection(),
        learner_highlights=_FOUR_HIGHLIGHTS,
        complete_fn=oracle,
    )
    system = oracle.last["system"]
    user = oracle.last["user"]
    # SYSTEM: the model is required to critique each highlight with the four assessments and to add a
    # per_learner_span array to the schema, with the partial-credit nuance spelled out.
    assert "PER-HIGHLIGHT CRITIQUE" in system
    assert '"per_learner_span"' in system
    for tier in ("'decisive'", "'excessive'", "'partial'", "'irrelevant'"):
        assert tier in system
    assert "2 of 3 decisive words" in system  # the partial-credit nuance example
    # USER: the deterministic word-coverage numbers are supplied as GUIDANCE, per highlight AND per gold
    # span, in both example phrasings from the plan.
    assert "PER-HIGHLIGHT COVERAGE" in user
    assert "PER-GOLD-SPAN COVERAGE" in user
    assert "5 decisive words inside a 5-word highlight" in user  # decisive
    assert "0 decisive words inside a 6-word highlight" in user  # irrelevant
    assert "overlaps NO gold span" in user
    assert "captured 5 of 5 decisive words" in user  # per-gold-span coverage


def test_per_learner_span_parsed_from_model_reply():
    two = _FOUR_HIGHLIGHTS[1:2] + _FOUR_HIGHLIGHTS[3:4]
    oracle = _oracle_client(
        json.dumps(
            {
                "highlight_grade": "somewhat",
                "explanation": "close",
                "per_learner_span": [
                    {
                        "quote": two[0]["text"],
                        "assessment": "too broad",  # synonym -> excessive
                        "note": "Trim to just the earnings figure.",
                    },
                    {
                        "quote": two[1]["text"],
                        "assessment": "partial",
                        "note": "Only the first half of the trade span.",
                    },
                ],
                "spans": [],
            }
        )
    )
    res = A.grade_semantic(
        PASSAGE,
        "unethical",
        "unethical",
        GOLD,
        [h["text"] for h in two],
        selection_indices=list(range(23, 34)) + [42, 43, 44],
        learner_highlights=two,
        complete_fn=oracle,
    )
    pls = res["per_learner_span"]
    assert [p["assessment"] for p in pls] == ["excessive", "partial"]
    assert pls[0]["quote"] == two[0]["text"]
    assert pls[0]["note"] == "Trim to just the earnings figure."
    # deterministic coverage numbers are attached alongside the model's words.
    assert pls[0]["decisive_words"] == 5 and pls[0]["highlight_words"] == 11


def test_multiple_learner_highlights_each_get_a_targeted_assessment():
    # AI-off: the deterministic derivation must still produce one critique row per highlight, in order,
    # covering all four tiers so the feedback maps to each thing the learner highlighted.
    res = A.grade_semantic(
        PASSAGE,
        "unethical",
        "unethical",
        GOLD,
        [h["text"] for h in _FOUR_HIGHLIGHTS],
        selection_indices=_four_highlight_selection(),
        learner_highlights=_FOUR_HIGHLIGHTS,
        complete_fn=_off_client,
    )
    pls = res["per_learner_span"]
    assert len(pls) == 4
    assert [p["assessment"] for p in pls] == [
        "decisive",
        "excessive",
        "irrelevant",
        "partial",
    ]
    # each row quotes the learner's OWN highlighted words
    assert [p["quote"] for p in pls] == [h["text"] for h in _FOUR_HIGHLIGHTS]
    # the excessive row explains WHY (too broad); the irrelevant row explains it does not help
    assert "too broad" in pls[1]["note"]
    assert pls[2]["decisive_words"] == 0


def test_fallback_emits_stable_per_learner_span_shape():
    # Even fully AI-off (and with only plain text spans, no token bounds), the fallback emits a
    # per_learner_span so the render + persisted payload shape is stable.
    res = A.grade_fallback(
        PASSAGE,
        "unethical",
        "unethical",
        GOLD,
        ["exact unreleased quarterly earnings figure"],
    )
    assert "per_learner_span" in res
    assert isinstance(res["per_learner_span"], list)
    row = res["per_learner_span"][0]
    assert row["quote"] == "exact unreleased quarterly earnings figure"
    assert row["assessment"] == "decisive"
    assert set(row) >= {"quote", "assessment", "note"}


def test_ai_path_derives_per_learner_span_when_model_omits_it():
    # A model reply with a valid grade but no per_learner_span still yields one derived row per
    # highlight so the UI always has a per-highlight critique to render.
    oracle = _oracle_client(json.dumps({"highlight_grade": "partial", "spans": []}))
    res = A.grade_semantic(
        PASSAGE,
        "unethical",
        "unethical",
        GOLD,
        ["spends the week assembling public filings"],
        selection_indices=list(range(4, 10)),
        learner_highlights=[
            {"text": "spends the week assembling public filings", "lo": 4, "hi": 9}
        ],
        complete_fn=oracle,
    )
    assert res["source"] == "ai"
    assert len(res["per_learner_span"]) == 1
    assert res["per_learner_span"][0]["assessment"] == "irrelevant"


def test_per_learner_span_assessment_is_sanitized():
    # Unknown/garbage assessments from the model fall back to the deterministic call, never crash.
    oracle = _oracle_client(
        json.dumps(
            {
                "highlight_grade": "somewhat",
                "per_learner_span": [
                    {"quote": "exact unreleased quarterly earnings figure", "assessment": "AMAZING"}
                ],
                "spans": [],
            }
        )
    )
    res = A.grade_semantic(
        PASSAGE,
        "unethical",
        "unethical",
        GOLD,
        ["exact unreleased quarterly earnings figure"],
        selection_indices=list(range(24, 29)),
        learner_highlights=[
            {"text": "exact unreleased quarterly earnings figure", "lo": 24, "hi": 28}
        ],
        complete_fn=oracle,
    )
    # garbage -> the deterministic derivation ("decisive" here), which is a valid assessment
    assert res["per_learner_span"][0]["assessment"] in A.LEARNER_SPAN_ASSESSMENTS
    assert res["per_learner_span"][0]["assessment"] == "decisive"
