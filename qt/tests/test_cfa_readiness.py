# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Exam Readiness is a native in-window state, not a bolted-on modal dialog.

Previously the top-bar "Readiness" tab opened ``ExamReadinessDialog(...).exec()``
— a modal QDialog — while Home / Study / Concept Map were first-class
main-window states, so Readiness read as a stock-Anki popup. It is now the
``cfaReadiness`` main-window state: the top-bar tab and the menu-bar entry both
open the SAME native screen, and the CFA top bar is redrawn so Home is always
one click away. Fails on stock Anki.
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from aqt import cfa_readiness

_REPO = Path(__file__).resolve().parents[2]


def test_readiness_is_a_main_window_state() -> None:
    src = (_REPO / "qt" / "aqt" / "main.py").read_text(encoding="utf-8")
    # the state exists in the literal, is dispatched, and is set up
    assert '"cfaReadiness"' in src
    assert "_cfaReadinessState" in src
    assert "def setupCfaReadiness" in src
    assert "self.setupCfaReadiness()" in src


def test_show_exam_readiness_routes_to_native_state() -> None:
    # aqt.cfa.show_exam_readiness now moves to the native state rather than
    # exec()-ing a modal dialog, so every caller (menu, Home, Concept Map) is
    # consistent with the top-bar tab.
    src = (_REPO / "qt" / "aqt" / "cfa.py").read_text(encoding="utf-8")
    start = src.index("def show_exam_readiness")
    end = src.index("\ndef ", start + 1)
    body = src[start:end]
    assert 'moveToState("cfaReadiness")' in body
    assert ".exec()" not in body


def test_toolbar_readiness_tab_moves_to_native_state() -> None:
    src = (_REPO / "qt" / "aqt" / "toolbar.py").read_text(encoding="utf-8")
    start = src.index("def _cfaReadinessLinkHandler")
    end = src.index("\n    def ", start + 1)
    body = src[start:end]
    assert 'moveToState("cfaReadiness")' in body


def test_controller_loads_the_whole_collection_readiness_page() -> None:
    # The overall readiness report is scored over the WHOLE collection (deck_id
    # 0), matching the CFA Home dashboard and the phone (both whole-collection),
    # so ethics-pair reviews and every CFA deck reach it. It must NOT scope to
    # whichever single deck happens to be current (which excluded ethics pairs).
    loaded: list[str] = []
    web = SimpleNamespace(
        set_bridge_command=lambda *a: None,
        load_sveltekit_page=lambda page: loaded.append(page),
        setFocus=lambda: None,
    )
    mw = SimpleNamespace(
        web=web,
        toolbar=SimpleNamespace(redraw=lambda: None),
        col=SimpleNamespace(decks=SimpleNamespace(get_current_id=lambda: 42)),
    )
    ctrl = cfa_readiness.CfaReadiness(mw)  # type: ignore[arg-type]
    ctrl.show()
    assert loaded == ["cfa-readiness/0"]


def test_link_handler_delegates_to_cfa_entry_points(monkeypatch) -> None:
    from aqt import cfa
    from aqt import cfa_home

    calls: list[str] = []
    monkeypatch.setattr(cfa, "study_by_exam_priority", lambda mw: calls.append("priority"))
    monkeypatch.setattr(cfa, "study_ethics_pairs", lambda mw: calls.append("ethics"))
    monkeypatch.setattr(cfa, "show_deadline", lambda mw: calls.append("deadline"))
    monkeypatch.setattr(cfa_home, "trigger_cfa_sync", lambda mw: calls.append("sync"))
    monkeypatch.setattr(cfa_home, "open_sync_settings", lambda mw: calls.append("sync-settings"))

    moved: list[str] = []
    mw = SimpleNamespace(web=object(), moveToState=lambda s: moved.append(s))
    ctrl = cfa_readiness.CfaReadiness(mw)  # type: ignore[arg-type]
    handler = ctrl._link_handler  # pylint: disable=protected-access

    for cmd in (
        "cfa:priority",
        "cfa:risk-session",
        "cfa:readiness-drill",
        "cfa:plan",
        "cfa:ethics",
        "cfa:deadline",
        "cfa:mock-review",
        "cfa:retention-queue",
        "cfa:mock-schedule",
        "cfa:sync",
        "cfa:sync-settings",
    ):
        handler(cmd)
    handler("cfa:conceptmap")
    handler("cfa:study")
    handler("cfa:readiness")
    handler("cfa:home")
    handler("cfa:decks")

    assert calls == [
        "priority",
        "priority",
        "priority",
        "priority",
        "ethics",
        "deadline",
        "deadline",
        "deadline",
        "deadline",
        "sync",
        "sync-settings",
    ]
    assert moved == ["cfaConceptMap", "cfaStudy", "cfaReadiness", "cfaHome", "deckBrowser"]
