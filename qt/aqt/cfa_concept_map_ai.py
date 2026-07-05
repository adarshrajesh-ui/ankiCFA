# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Concept Map bridge — the SINGLE batched AI explanation call over pycmd.

When the Concept Map tab opens it draws instantly from the deterministic
templated explanations baked into the pure ``conceptmap`` engine. If AI is on it
ALSO fires ONE batched call: the page sends every node's ``{id, full, kind, pct,
band, parent}`` via

    bridgeCommand("cfaExplainMap:" + JSON.stringify({nodes}), (resp) => { ... })

and this module answers with a JSON string ``{ok, aiOn, explanations, error,
model}``. The page merges the returned per-id wording over its templates and
shows honest provenance ("AI-generated" vs "AI off — templated" vs "AI failed
— templated"). With AI off (master toggle off, or no key) the bridge returns
``ok=False, aiOn=False`` immediately — no network — so the tab is fully offline.

The heavy lifting is the pure, ``anki``-free :func:`cfa.ai.mapexplain.explain_map`;
:func:`handle_explain_request` is a thin, unit-testable adapter and
:func:`_on_js_message` wires it into ``gui_hooks``.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from aqt import gui_hooks

_MSG_PREFIX = "cfaExplainMap:"

# The repo root MUST be on sys.path so ``from cfa.ai... import`` resolves in the
# running app; without it the batched call is unreachable and every explanation
# silently stays templated (the "always fallback" bug the ethics bridge hit).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _ensure_path() -> None:
    if os.path.isdir(_REPO_ROOT) and _REPO_ROOT not in sys.path:
        sys.path.insert(0, _REPO_ROOT)


def _map_ai_enabled() -> bool:
    """Whether the Concept Map's AI explanations are enabled by the toggles.

    Gated on the shared MASTER AI switch (default ON): the batched explanation is
    a read-only narration layered on the same scores the two headline AI features
    already gate individually, so it honours the one switch the user flips to go
    fully offline rather than adding a third control. Returns True when the
    collection is unavailable (``explain_map`` still degrades safely if the key
    or call fails)."""
    try:
        import aqt

        from aqt.cfa_ai_settings import get_ai_toggles

        col = getattr(getattr(aqt, "mw", None), "col", None)
        if col is None:
            return True
        return bool(get_ai_toggles(col)["master"])
    except Exception:  # pragma: no cover - defensive; never block the tab
        return True


def handle_explain_request(
    payload: dict[str, Any], *, force_fallback: bool = False
) -> dict[str, Any]:
    """Answer one batched-explanation request from the map JS. Never raises.

    ``payload`` is ``{"nodes": [{id, full, kind, pct, band, parent}, ...]}``.
    When ``force_fallback`` is True (master AI off) returns immediately with
    ``ok=False, aiOn=False, error="ai_off"`` — no LLM call — so turning AI off is
    instant and offline. Otherwise makes the single batched call and returns its
    result with ``aiOn=True``.
    """
    nodes = payload.get("nodes") if isinstance(payload, dict) else None

    if force_fallback:
        return {
            "ok": False,
            "aiOn": False,
            "explanations": {},
            "error": "ai_off",
            "model": None,
        }

    _ensure_path()
    try:
        from cfa.ai.mapexplain import explain_map
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "ok": False,
            "aiOn": True,
            "explanations": {},
            "error": f"import_error:{type(exc).__name__}",
            "model": None,
        }

    result = explain_map(nodes)
    return {
        "ok": bool(result.get("ok")),
        "aiOn": True,
        "explanations": result.get("explanations") or {},
        "error": result.get("error"),
        "model": result.get("model"),
    }


def _on_js_message(
    handled: tuple[bool, Any], message: str, context: Any
) -> tuple[bool, Any]:
    """gui_hooks.webview_did_receive_js_message handler for the explain bridge.

    Returns ``(True, json_string)`` when it owns the message (the page's callback
    JSON.parses the string), else passes ``handled`` through untouched.
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
    result = handle_explain_request(payload, force_fallback=not _map_ai_enabled())
    return (True, json.dumps(result))


_REGISTERED = False


def register() -> None:
    """Register the concept-map explain bridge exactly once (idempotent)."""
    global _REGISTERED
    if _REGISTERED:
        return
    gui_hooks.webview_did_receive_js_message.append(_on_js_message)
    _REGISTERED = True


__all__ = ["handle_explain_request", "register"]
