# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Increment 2 (desktop-shell): CFA Home is the native landing screen.

Covers the Home payload shape (three honest scores + exam countdown + AI state),
the mediasrv route/endpoint/whitelist wiring, the main-window landing change,
and the CTA bridge routing to the existing CFA entry points. Each assertion
fails on stock ankiCFA (before this increment) and passes after.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from anki.collection import Collection

import aqt.cfa_home as cfa_home
import aqt.mediasrv as mediasrv
from aqt.webview import AnkiWebViewKind

_REPO = Path(__file__).resolve().parents[2]


def _empty_col() -> Collection:
    fd, path = tempfile.mkstemp(suffix=".anki2")
    os.close(fd)
    os.unlink(path)
    return Collection(path)


def test_home_payload_shape() -> None:
    col = _empty_col()
    try:
        payload = mediasrv._cfa_home_payload(col)
    finally:
        col.close()

    # three honest score bands, each with the shared range/abstain contract
    for key in ("memory", "performance", "readiness"):
        band = payload[key]
        for field in ("abstain", "reason", "point", "rangeLow", "rangeHigh"):
            assert field in band, f"{key} band missing {field}"

    # Home-specific chrome: exam countdown + AI state
    assert "examDate" in payload
    assert "daysToExam" in payload
    assert "aiEnabled" in payload
    assert payload["sync"]["actionLabel"] == "Connect & Sync"
    assert payload["sync"]["status"] == "Offline until connected"
    assert payload["heroMode"] in ("abstain", "bayesian_call")


def test_home_ai_flag_reflects_config() -> None:
    col = _empty_col()
    try:
        # AI-first: defaults ON when unset.
        assert mediasrv._cfa_home_payload(col)["aiEnabled"] is True
        col.set_config("cfa_ai_enabled", False)
        assert mediasrv._cfa_home_payload(col)["aiEnabled"] is False
    finally:
        col.close()


def test_home_endpoint_registered_and_served() -> None:
    # POST handler registered -> exposed as /_anki/getCfaHomeView
    assert mediasrv.get_cfa_home_view in mediasrv.post_handler_list
    # route served by mediasrv
    assert mediasrv.is_sveltekit_page("cfa-home") is True
    assert mediasrv.is_sveltekit_page("cfa-home/x") is True
    # whitelisted for the main webview (no API token), like congratsInfo
    src = (_REPO / "qt" / "aqt" / "mediasrv.py").read_text(encoding="utf-8")
    assert '"/_anki/getCfaHomeView"' in src


def test_cfa_home_webview_kind_has_api_access() -> None:
    assert AnkiWebViewKind.CFA_HOME.value == "cfa home"
    wv_src = (_REPO / "qt" / "aqt" / "webview.py").read_text(encoding="utf-8")
    assert "AnkiWebViewKind.CFA_HOME," in wv_src


def test_landing_moves_to_cfa_home() -> None:
    src = (_REPO / "qt" / "aqt" / "main.py").read_text(encoding="utf-8")
    # the state exists and is dispatched
    assert '"cfaHome"' in src
    assert "_cfaHomeState" in src
    assert "def setupCfaHome" in src
    # profile load lands on CFA Home, not the deck browser
    assert 'self.moveToState("cfaHome")' in src


def test_link_handler_routes_ctas_to_cfa_entry_points(monkeypatch) -> None:
    import aqt.cfa as cfa
    import aqt.cfa_sync_connect as sync_connect

    calls: list[str] = []
    monkeypatch.setattr(cfa, "study_ethics_pairs", lambda mw: calls.append("ethics"))
    monkeypatch.setattr(cfa, "study_by_exam_priority", lambda mw: calls.append("priority"))
    monkeypatch.setattr(cfa, "show_exam_readiness", lambda mw: calls.append("readiness"))
    monkeypatch.setattr(cfa, "show_deadline", lambda mw: calls.append("deadline"))
    monkeypatch.setattr(cfa_home, "open_ai_settings", lambda mw: calls.append("ai"))
    monkeypatch.setattr(sync_connect, "connect_cfa_sync", lambda mw: calls.append("sync"))

    moved: list[str] = []
    mw = SimpleNamespace(web=object(), moveToState=lambda s: moved.append(s))
    home = cfa_home.CfaHome(mw)  # type: ignore[arg-type]

    for cmd in (
        "cfa:ethics",
        "cfa:priority",
        "cfa:readiness",
        "cfa:deadline",
        "cfa:ai",
        "cfa:sync",
    ):
        home._link_handler(cmd)
    home._link_handler("cfa:decks")

    assert calls == ["ethics", "priority", "readiness", "deadline", "ai", "sync"]
    assert moved == ["deckBrowser"]
