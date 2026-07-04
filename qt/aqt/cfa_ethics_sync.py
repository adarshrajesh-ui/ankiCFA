#!/usr/bin/env python3
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA sync — persist ethics attempt detail into card.custom_data (increment 5).

When the ethics card reveals a grade it stores the W3 attempt-detail payload in
``localStorage["cfaEthics:pending"]``. On desktop we read that payload when the
answer side is shown and merge it into ``card.custom_data`` under the
``cfaEthic`` namespace (Anki limits custom_data keys to 8 bytes).

``custom_data`` syncs through the normal Anki sync engine, so a highlighted
ethics attempt made on desktop crosses to other devices after sync.
"""

from __future__ import annotations

import json
from typing import Any

from aqt import gui_hooks

# Anki custom_data top-level keys must be <= 8 bytes.
CFA_ETHICS_NAMESPACE = "cfaEthic"
_LOCAL_STORAGE_KEY = "cfaEthics:pending"


def persist_ethics_attempt(col, card, payload: dict[str, Any]) -> None:
    """Write a compact ethics summary into ``card.custom_data[CFA_ETHICS_NAMESPACE]``."""
    from anki import cfa_sync as cs

    if not payload.get("completed"):
        return
    cs.merge_custom_data(
        col, card.id, CFA_ETHICS_NAMESPACE, cs.compact_ethics_payload(payload)
    )


def _on_show_answer(reviewer, card) -> None:
    """Read the pending ethics payload from the reviewer webview and persist it."""

    def _cb(raw: Any) -> None:
        if not raw or raw in ("null", ""):
            return
        try:
            payload = json.loads(str(raw))
        except (TypeError, ValueError):
            return
        if not isinstance(payload, dict):
            return
        persist_ethics_attempt(reviewer.mw.col, card, payload)

    reviewer.web.evalWithCallback(
        f"localStorage.getItem({json.dumps(_LOCAL_STORAGE_KEY)})", _cb
    )


_REGISTERED = False


def register() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    gui_hooks.reviewer_did_show_answer.append(_on_show_answer)
    _REGISTERED = True


__all__ = ["CFA_ETHICS_NAMESPACE", "persist_ethics_attempt", "register"]
