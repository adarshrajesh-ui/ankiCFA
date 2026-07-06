# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""F2 desktop bridge tests — the pycmd -> semantic grader adapter.

Exercises ``aqt.cfa_ethics_ai`` end-to-end without a live webview: a JSON pycmd
payload in, a JSON string out, going through the real ``ai_grading`` module.
With AI off (the default here) the bridge returns the deterministic fallback,
proving the review is never blocked when there is no OpenAI key.
"""

import json

import pytest

pytest.importorskip("aqt")

from aqt.cfa_ethics_ai import (  # noqa: E402
    _ensure_path,
    _grading_ai_enabled,
    _on_js_message,
    handle_grade_request,
    register,
)

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


def _payload(**over):
    p = {
        "itemId": "PSG-01",
        "passage": PASSAGE,
        "answerVerdict": "unethical",
        "judgedVerdict": "unethical",
        "goldSpans": GOLD,
        "learnerSpans": [g["phrase"] for g in GOLD],
        "selectionIndices": None,
    }
    p.update(over)
    return p


def test_handle_grade_request_fallback_correct():
    # force_fallback -> deterministic path, no network, regardless of any key.
    res = handle_grade_request(_payload(), force_fallback=True)
    assert res["source"] == "fallback"
    assert res["error"] == "ai_off"
    assert res["grade"] == "correct" and res["correct"] is True
    # must be JSON-serializable (it is sent to JS as a string)
    json.dumps(res)


def test_handle_grade_request_forwards_structured_highlights():
    res = handle_grade_request(
        _payload(
            learnerSpans=["whole passage"],
            learnerHighlights=[{"text": "whole passage", "lo": 0, "hi": 40}],
            selectionIndices=list(range(0, 41)),
        ),
        force_fallback=True,
    )
    assert res["source"] == "fallback"
    assert res["evidence_precision"] == "overbroad"
    assert "whole passage" in res["learner_intent"]
    json.dumps(res)


def test_ensure_path_makes_llm_client_importable():
    # Regression: the "always deterministic fallback" bug was ai_grading's
    # `from cfa.ai.llm_client import complete` failing because the repo root was
    # not on sys.path. _ensure_path() must fix that.
    import importlib

    _ensure_path()
    mod = importlib.import_module("cfa.ai.llm_client")
    assert hasattr(mod, "complete")


def test_grading_ai_enabled_defaults_on():
    # With no live collection, ethics AI grading defaults ON (AI-first).
    assert _grading_ai_enabled() is True


def test_handle_grade_request_wrong_verdict():
    res = handle_grade_request(_payload(judgedVerdict="ethical"))
    assert res["verdict_correct"] is False and res["correct"] is False


def test_handle_grade_request_tolerates_garbage_payload():
    res = handle_grade_request({"passage": PASSAGE})  # missing everything else
    assert "grade" in res and res["source"] in ("fallback", "ai")
    json.dumps(res)


def test_on_js_message_owns_prefixed_message_only():
    # a non-CFA message passes through untouched
    passthrough = _on_js_message((False, None), "somethingElse", None)
    assert passthrough == (False, None)
    # already-handled messages are left alone
    already = _on_js_message((True, "x"), "cfaGradeEthics:{}", None)
    assert already == (True, "x")


def test_on_js_message_returns_json_string():
    handled, out = _on_js_message(
        (False, None), "cfaGradeEthics:" + json.dumps(_payload()), None
    )
    assert handled is True
    parsed = json.loads(out)  # JS side does JSON.parse(res)
    assert parsed["grade"] == "correct"


def test_on_js_message_bad_json_still_answers():
    handled, out = _on_js_message((False, None), "cfaGradeEthics:{not json", None)
    assert handled is True
    parsed = json.loads(out)
    assert "grade" in parsed


def test_register_is_idempotent():
    from aqt import gui_hooks

    register()
    n1 = len(gui_hooks.webview_did_receive_js_message._hooks)
    register()
    n2 = len(gui_hooks.webview_did_receive_js_message._hooks)
    assert n1 == n2
