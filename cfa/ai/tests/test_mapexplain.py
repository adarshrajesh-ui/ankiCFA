# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Tests for the Concept Map's single batched AI explanation call.

All offline: an injected ``complete_fn`` stands in for the LLM, so we exercise
the batched-prompt shape, robust JSON parsing, the abstain (give-up) wording,
and every failure path (no key, malformed JSON, empty map) without a network.
"""

import json

from cfa.ai.mapexplain import (
    _clean_nodes,
    _extract_json_object,
    build_batch_messages,
    explain_map,
)

NODES = [
    {"id": "cfa", "full": "Overall CFA readiness", "kind": "cfa", "pct": 58, "band": None, "parent": None},
    {"id": "topic:equity", "full": "Equity Investments", "kind": "topic", "pct": 71, "band": "10–15%", "parent": None},
    {"id": "topic:altinv", "full": "Alternative Investments", "kind": "topic", "pct": None, "band": "5–10%", "parent": None},
    {"id": "sub:equity:FCFE / FCFF", "full": "FCFE / FCFF", "kind": "sub", "pct": 71, "band": None, "parent": "Equity Investments"},
]


def _ok_completion_from(mapping):
    """A fake complete() that returns `mapping` as a JSON object reply."""

    def _fn(system, user, **kw):
        return {"ok": True, "text": json.dumps(mapping), "model": "gpt-4o-test"}

    return _fn


def test_clean_nodes_drops_bad_and_dedupes():
    dirty = [
        {"id": "a", "full": "A", "kind": "topic", "pct": "62"},
        {"id": "a", "full": "dup", "kind": "topic", "pct": 1},  # duplicate id dropped
        {"id": "", "full": "no id"},  # no id dropped
        "not a dict",  # non-dict dropped
        {"id": "b", "pct": None},
    ]
    clean = _clean_nodes(dirty)
    ids = [n["id"] for n in clean]
    assert ids == ["a", "b"]
    assert clean[0]["pct"] == 62  # coerced "62" -> 62
    assert clean[1]["pct"] is None  # abstain preserved
    assert clean[1]["full"] == "b"  # falls back to id


def test_build_messages_marks_abstain_and_ids():
    system, user = build_batch_messages(_clean_nodes(NODES))
    assert "JSON" in system and "null" in system.lower()
    # every node id appears so the model can key its reply
    for n in NODES:
        assert n["id"] in user
    # the abstaining node is flagged, the scored ones carry a percent
    assert "abstaining" in user
    assert "71%" in user


def test_extract_json_handles_fences_and_prose():
    obj = {"cfa": "hi"}
    assert _extract_json_object(json.dumps(obj)) == obj
    assert _extract_json_object("```json\n" + json.dumps(obj) + "\n```") == obj
    assert _extract_json_object("Sure! " + json.dumps(obj) + " done.") == obj
    assert _extract_json_object("no json here") is None
    assert _extract_json_object("") is None


def test_explain_map_success_filters_to_known_ids():
    reply = {
        "cfa": "You're at about 58% overall — study your dim heavy sections.",
        "topic:equity": "Equity is solid at 71%.",
        "topic:altinv": "Not enough graded reviews yet, so it's abstaining.",
        "sub:equity:FCFE / FCFF": "Reflects the Equity estimate.",
        "topic:ghost": "this id was never sent — must be dropped",
        "topic:blank": "",
    }
    res = explain_map(NODES, complete_fn=_ok_completion_from(reply))
    assert res["ok"] is True
    assert res["model"] == "gpt-4o-test"
    assert "topic:ghost" not in res["explanations"]  # unknown id filtered
    assert set(res["explanations"]) == {
        "cfa",
        "topic:equity",
        "topic:altinv",
        "sub:equity:FCFE / FCFF",
    }
    assert res["count"] == 4


def test_explain_map_no_key_is_safe():
    def _no_key(system, user, **kw):
        return {"ok": False, "text": "", "error": "no_api_key", "model": "gpt-4o"}

    res = explain_map(NODES, complete_fn=_no_key)
    assert res["ok"] is False
    assert res["error"] == "no_api_key"
    assert res["explanations"] == {}


def test_explain_map_bad_json_falls_back():
    def _garbage(system, user, **kw):
        return {"ok": True, "text": "here is your map: not json at all", "model": "m"}

    res = explain_map(NODES, complete_fn=_garbage)
    assert res["ok"] is False
    assert res["error"] == "bad_json"
    assert res["explanations"] == {}


def test_explain_map_empty_map_when_no_known_ids():
    res = explain_map(NODES, complete_fn=_ok_completion_from({"ghost": "x"}))
    assert res["ok"] is False
    assert res["error"] == "empty_map"


def test_explain_map_no_nodes():
    res = explain_map([], complete_fn=_ok_completion_from({"a": "b"}))
    assert res["ok"] is False
    assert res["error"] == "no_nodes"


def test_explain_map_never_raises_on_client_exception():
    def _boom(system, user, **kw):
        raise RuntimeError("network exploded")

    res = explain_map(NODES, complete_fn=_boom)
    assert res["ok"] is False
    assert res["error"].startswith("client_error:")
    assert res["explanations"] == {}
