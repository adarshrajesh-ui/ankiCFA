# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Concept Map bridge tests — the pycmd -> batched explain adapter.

Exercises ``aqt.cfa_concept_map_ai`` without a live webview: a JSON pycmd payload
in, a JSON string out. With AI forced off the bridge returns the ``ai_off``
marker and never calls out, proving the tab stays fully offline + templated when
the master AI toggle is off.
"""

import json

import pytest

pytest.importorskip("aqt")

from aqt.cfa_concept_map_ai import (  # noqa: E402
    _MSG_PREFIX,
    _on_js_message,
    handle_explain_request,
    register,
)

PAYLOAD = {
    "nodes": [
        {"id": "cfa", "full": "Overall CFA readiness", "kind": "cfa", "pct": 58, "band": None, "parent": None},
        {"id": "topic:equity", "full": "Equity Investments", "kind": "topic", "pct": 71, "band": "10–15%", "parent": None},
    ]
}


def test_force_fallback_is_ai_off_and_offline():
    res = handle_explain_request(PAYLOAD, force_fallback=True)
    assert res["aiOn"] is False
    assert res["ok"] is False
    assert res["error"] == "ai_off"
    assert res["explanations"] == {}


def test_ai_on_returns_valid_shape_either_way():
    # AI on -> the bridge always reports aiOn=True and a well-formed result,
    # whether or not an OPENAI_API_KEY happens to be configured in this env.
    # With a key the real batched call fills `explanations` keyed by the sent
    # ids; without one it degrades to ok=False + an empty map (never raises).
    res = handle_explain_request(PAYLOAD, force_fallback=False)
    assert res["aiOn"] is True
    assert isinstance(res["explanations"], dict)
    sent_ids = {n["id"] for n in PAYLOAD["nodes"]}
    if res["ok"]:
        assert res["explanations"]  # at least one node explained
        assert set(res["explanations"]).issubset(sent_ids)  # only known ids
        assert all(isinstance(v, str) and v.strip() for v in res["explanations"].values())
    else:
        assert res["explanations"] == {}
        assert res["error"]  # a structured reason is always present


def test_on_js_message_owns_prefix_returns_json_string():
    msg = _MSG_PREFIX + json.dumps(PAYLOAD)
    handled, out = _on_js_message((False, None), msg, None)
    assert handled is True
    parsed = json.loads(out)
    assert "explanations" in parsed and "aiOn" in parsed


def test_on_js_message_passes_through_foreign_messages():
    sentinel = (False, "nope")
    assert _on_js_message(sentinel, "someOtherCmd:xyz", None) == sentinel
    # already-handled messages are never touched
    already = (True, "prev")
    assert _on_js_message(already, _MSG_PREFIX + "{}", None) == already


def test_on_js_message_tolerates_malformed_json():
    handled, out = _on_js_message((False, None), _MSG_PREFIX + "{bad json", None)
    assert handled is True
    parsed = json.loads(out)
    # empty payload -> no nodes -> ok False, but never raises
    assert parsed["ok"] is False


def test_register_is_idempotent():
    register()
    register()  # second call must not raise or double-register
