# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Study statistics is a native in-window CFA nav tab, not a menu-bar-only dialog.

For a CFA exam-prep product, "how am I tracking" is core, yet the themed
statistics/graphs page was reachable ONLY from Anki's menu bar — the CFA top-bar
nav had no Progress entry. It is now the ``cfaProgress`` main-window state: a
"Progress" top-bar tab loads the themed graphs page into the main webview
(mirroring Readiness / Concept Map), the CFA top bar is redrawn so Home is one
click away, and the current-tab highlight tracks it. Fails on stock Anki.
"""

# pylint: disable=protected-access

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from aqt import cfa_progress

_REPO = Path(__file__).resolve().parents[2]


def test_progress_is_a_main_window_state() -> None:
    src = (_REPO / "qt" / "aqt" / "main.py").read_text(encoding="utf-8")
    assert '"cfaProgress"' in src
    assert "_cfaProgressState" in src
    assert "def setupCfaProgress" in src
    assert "self.setupCfaProgress()" in src


def test_toolbar_exposes_progress_tab_moving_to_native_state() -> None:
    src = (_REPO / "qt" / "aqt" / "toolbar.py").read_text(encoding="utf-8")
    # the nav link is registered with an id we can highlight...
    assert '"cfa_progress",' in src
    assert '"Progress",' in src
    # ...the active-tab map knows about it...
    assert '"cfaProgress": "cfa_progress",' in src
    # ...and its handler moves to the native state (no modal dialog).
    start = src.index("def _cfaProgressLinkHandler")
    end = src.index("\n    def ", start + 1)
    body = src[start:end]
    assert 'moveToState("cfaProgress")' in body


def test_controller_loads_the_themed_graphs_page() -> None:
    loaded: list[str] = []
    web = SimpleNamespace(
        set_bridge_command=lambda *a: None,
        load_sveltekit_page=lambda page: loaded.append(page),
        setFocus=lambda: None,
    )
    mw = SimpleNamespace(
        web=web,
        toolbar=SimpleNamespace(redraw=lambda: None),
    )
    ctrl = cfa_progress.CfaProgress(mw)  # type: ignore[arg-type]
    ctrl.show()
    assert loaded == ["graphs"]


def test_sync_refresh_map_covers_progress_page() -> None:
    from aqt import cfa_sync_connect as cc

    assert cc._CFA_STATE_PAGES["cfaProgress"] == "graphs"


def test_link_handler_opens_browser_on_chart_drill_in(monkeypatch) -> None:
    # Clicking a bar in a graph emits `browserSearch: <query>`; the native state
    # must honour it exactly like the NewDeckStats dialog did, opening the
    # Browser filtered to those cards.
    import aqt

    searched: list[str] = []
    fake_browser = SimpleNamespace(search_for=lambda q: searched.append(q))
    monkeypatch.setattr(aqt.dialogs, "open", lambda name, mw: fake_browser)

    mw = SimpleNamespace(web=object())
    ctrl = cfa_progress.CfaProgress(mw)  # type: ignore[arg-type]
    handled = ctrl._link_handler("browserSearch: deck:current added:1")

    assert handled is False
    assert searched == [" deck:current added:1"]


def test_link_handler_routes_phone_product_nav() -> None:
    moved: list[str] = []
    mw = SimpleNamespace(web=object(), moveToState=moved.append)
    ctrl = cfa_progress.CfaProgress(mw)  # type: ignore[arg-type]

    ctrl._link_handler("cfa:home")
    ctrl._link_handler("cfa:study")
    ctrl._link_handler("cfa:conceptmap")
    ctrl._link_handler("cfa:readiness")
    ctrl._link_handler("cfa:progress")

    assert moved == [
        "cfaHome",
        "cfaStudy",
        "cfaConceptMap",
        "cfaReadiness",
        "cfaProgress",
    ]
