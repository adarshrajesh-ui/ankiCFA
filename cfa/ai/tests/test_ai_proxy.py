# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Unit tests for the mobile AI proxy (tools/cfa/ai_proxy.py).

Deterministic: the LLM is injected via ``complete_fn`` so no network/key is
needed. Exercises the AI path and the AI-off fallback contract (source flips to
"fallback" on any failure), plus token gating.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
for _p in (os.path.join(_ROOT, "tools", "cfa"), os.path.join(_ROOT, "cfa", "ethics_pairs"), _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ai_proxy  # noqa: E402


def _ok(*a, **k):
    return {"ok": True, "text": "Front-running is trading ahead of client orders.",
            "model": "gpt-4o-mini", "error": None, "usage": {}}


def _fail(*a, **k):
    return {"ok": False, "text": "", "model": None, "error": "rate_limit", "usage": {}}


def test_fill_front_to_back():
    r = ai_proxy.fill(front="Define front-running.", back="", complete_fn=_ok)
    assert r["ok"] is True
    assert r["target"] == "back"
    assert r["source"] == "ai"
    assert r["model"] == "gpt-4o-mini"


def test_fill_back_to_front():
    r = ai_proxy.fill(front="", back="Front-running: trading ahead of client orders.", complete_fn=_ok)
    assert r["ok"] is True
    assert r["target"] == "front"
    assert r["source"] == "ai"


def test_fill_nothing_when_both_empty():
    r = ai_proxy.fill(front="  ", back="", complete_fn=_ok)
    assert r["source"] == "fallback"
    assert r["error"] == "nothing_to_fill"


def test_fill_nothing_when_both_filled():
    r = ai_proxy.fill(front="Q", back="A", complete_fn=_ok)
    assert r["source"] == "fallback"
    assert r["error"] == "nothing_to_fill"


def test_fill_falls_back_on_failure():
    r = ai_proxy.fill(front="Define front-running.", complete_fn=_fail)
    assert r["ok"] is False
    assert r["source"] == "fallback"
    assert r["target"] == "back"
    assert r["error"] == "rate_limit"


def test_grade_ai_path():
    r = ai_proxy.grade(
        {
            "passage": "She traded ahead of her clients.",
            "answerVerdict": "unethical",
            "judgedVerdict": "unethical",
            "goldSpans": [{"phrase": "traded ahead of her clients", "rationale": "front-running"}],
            "learnerSpans": ["traded ahead of her clients"],
        },
        complete_fn=lambda **k: {
            "ok": True,
            "text": '{"verdict_correct": true, "highlight_grade": "correct", "explanation": "nailed it", "spans": [{"phrase":"traded ahead of her clients","matched":true,"note":""}]}',
            "model": "gpt-4o-mini",
            "error": None,
            "usage": {},
        },
    )
    assert r["source"] == "ai"
    assert r["grade"] == "correct"


def test_grade_falls_back():
    r = ai_proxy.grade(
        {
            "passage": "x",
            "answerVerdict": "unethical",
            "judgedVerdict": "unethical",
            "goldSpans": [{"phrase": "x"}],
            "learnerSpans": ["x"],
        },
        complete_fn=_fail,
    )
    assert r["source"] == "fallback"


def test_token_default():
    # The gate token is NOT the OpenAI key.
    assert ai_proxy._token() == ai_proxy.DEFAULT_TOKEN
    assert "sk-" not in ai_proxy._token()
