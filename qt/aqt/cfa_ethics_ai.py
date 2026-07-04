# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""F2 desktop bridge — semantic AI grading of ethics highlights over pycmd.

The one-passage ethics card grades its highlight deterministically in JS so it
works instantly on AnkiDroid and with AI OFF. On desktop it ALSO asks Python for
a *semantic* grade: the front template calls

    pycmd("cfaGradeEthics:" + JSON.stringify(payload), function (resp) { ... })

and this module answers with a JSON string the card renders as an extra
"AI feedback" block. If AI is off (no ``OPENAI_API_KEY``) the semantic grader
falls straight back to the deterministic F1 grade, so the bridge always returns
something useful and never blocks the review.

The heavy lifting lives in the pure, ``anki``-free ``cfa/ethics_pairs/
ai_grading.py``; :func:`handle_grade_request` is a thin, unit-testable adapter,
and :func:`_on_js_message` wires it into ``gui_hooks``.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from aqt import gui_hooks

_MSG_PREFIX = "cfaGradeEthics:"

# ai_grading lives under cfa/ethics_pairs (a PEP-420 namespace dir, imported by
# path here so aqt does not depend on the repo layout being importable).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ETHICS_DIR = os.path.join(_REPO_ROOT, "cfa", "ethics_pairs")


def _ensure_path() -> None:
    # The repo root MUST be on sys.path so ``ai_grading``'s
    # ``from cfa.ai.llm_client import complete`` resolves — without it the LLM is
    # unreachable and every grade silently degrades to the deterministic
    # fallback (the "always fallback" bug). ``cfa/ethics_pairs`` is also added so
    # ``import ai_grading`` works as a top-level module.
    for path in (_REPO_ROOT, _ETHICS_DIR):
        if path and os.path.isdir(path) and path not in sys.path:
            sys.path.insert(0, path)


def _grading_ai_enabled() -> bool:
    """Whether the ethics AI grading toggle is ON (default ON).

    Reads the shared col.conf toggle via the collection; defaults ON so ethics
    grading uses AI out of the box, and returns True when the collection is
    unavailable (grade_semantic still falls back safely if the key/call fails)."""
    try:
        import aqt

        from aqt.cfa_ai_settings import ai_active

        col = getattr(getattr(aqt, "mw", None), "col", None)
        if col is None:
            return True
        return bool(ai_active(col, "grading"))
    except Exception:  # pragma: no cover - defensive; never block grading
        return True


def handle_grade_request(
    payload: dict[str, Any], *, force_fallback: bool = False
) -> dict[str, Any]:
    """Grade one attempt payload from the card JS. Never raises.

    Expected payload keys (all optional-tolerant):
        passage, answerVerdict, judgedVerdict,
        goldSpans: [{phrase, rationale}], learnerSpans: [str],
        selectionIndices: [int]
    Returns the ``ai_grading.grade_semantic`` result dict (JSON-serializable).

    When ``force_fallback`` is True (the AI grading toggle is OFF), the
    deterministic F1 grade is returned directly with ``error == "ai_off"`` — no
    LLM call — so turning AI off is instant and offline.
    """
    _ensure_path()
    try:
        from ai_grading import grade_fallback, grade_semantic
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "ok": False,
            "source": "fallback",
            "grade": "wrong",
            "correct": False,
            "explanation": "AI grading unavailable on this build.",
            "per_span": [],
            "error": f"import_error:{type(exc).__name__}",
            "model": None,
        }

    passage = str(payload.get("passage", ""))
    answer_verdict = str(payload.get("answerVerdict", ""))
    judged_verdict = str(payload.get("judgedVerdict", ""))
    gold_spans = payload.get("goldSpans") or []
    if not isinstance(gold_spans, list):
        gold_spans = []
    learner_spans = payload.get("learnerSpans") or []
    if not isinstance(learner_spans, list):
        learner_spans = []
    selection = payload.get("selectionIndices")
    if not isinstance(selection, list):
        selection = None
    spans = [str(p) for p in learner_spans]
    sel = [int(i) for i in selection] if selection else None
    item_id = str(payload.get("itemId", ""))
    standard = str(payload.get("standard", ""))

    if force_fallback:
        # AI toggled OFF: deterministic grade, no network. error="ai_off" tells
        # the card this is an intentional off-state (not a failure), so it does
        # not show an "AI unavailable" warning.
        return grade_fallback(
            passage,
            answer_verdict,
            judged_verdict,
            gold_spans,
            spans,
            sel,
            error="ai_off",
            item_id=item_id,
            standard=standard,
        )

    try:
        return grade_semantic(
            passage,
            answer_verdict,
            judged_verdict,
            gold_spans,
            spans,
            selection_indices=sel,
            item_id=item_id,
            standard=standard,
        )
    except (
        Exception
    ) as exc:  # pragma: no cover - grade_semantic is no-raise, belt+braces
        return grade_fallback(
            passage,
            answer_verdict,
            judged_verdict,
            gold_spans,
            spans,
            sel,
            error=f"bridge_error:{type(exc).__name__}",
            item_id=item_id,
            standard=standard,
        )


def _on_js_message(
    handled: tuple[bool, Any], message: str, context: Any
) -> tuple[bool, Any]:
    """gui_hooks.webview_did_receive_js_message handler for the grading bridge.

    Returns ``(True, json_string)`` when it owns the message (the card's pycmd
    callback JSON.parses the string), else passes ``handled`` through untouched.
    """
    if (
        handled[0]
        or not isinstance(message, str)
        or not message.startswith(_MSG_PREFIX)
    ):
        return handled
    raw = message[len(_MSG_PREFIX) :]
    try:
        payload = json.loads(raw) if raw else {}
        if not isinstance(payload, dict):
            payload = {}
    except ValueError:
        payload = {}
    result = handle_grade_request(payload, force_fallback=not _grading_ai_enabled())
    return (True, json.dumps(result))


_REGISTERED = False


def register() -> None:
    """Register the grading bridge exactly once (idempotent)."""
    global _REGISTERED
    if _REGISTERED:
        return
    gui_hooks.webview_did_receive_js_message.append(_on_js_message)
    _REGISTERED = True


__all__ = ["handle_grade_request", "register"]
