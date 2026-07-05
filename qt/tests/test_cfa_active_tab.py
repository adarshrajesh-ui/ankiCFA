# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""The CFA top-bar nav shows WHICH section you're in (active-tab marker).

Stock Anki's toolbar has no active-tab concept, so the CFA nav (Home / Study /
Concept Map / Readiness) rendered as an undifferentiated row of links — a product nav
should always highlight the current section. The toolbar now marks the tab for
the current main-window state with `is-active` + `aria-current="page"` (styled
as a filled accent pill by cfa_chrome), and clears it on every state change so
leaving a CFA screen for the deck list or a study session never leaves a stale
"you are here" pill lit. Fails on stock Anki. (Phase B Pass 4 — D-P4-2.)
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from aqt import toolbar

_REPO = Path(__file__).resolve().parents[2]


def _toolbar(state: str):
    evals: list[str] = []
    web = SimpleNamespace(eval=lambda js: evals.append(js))
    web.requiresCol = None
    mw = SimpleNamespace(state=state)
    tb = toolbar.Toolbar(mw, web)  # type: ignore[arg-type]
    return tb, evals


def test_state_tab_mapping_covers_the_native_cfa_states() -> None:
    m = toolbar.Toolbar._CFA_STATE_TABS
    assert m == {
        "cfaHome": "cfa_home",
        "cfaStudy": "cfa_study",
        "cfaConceptMap": "cfa_concept_map",
        "cfaReadiness": "cfa_readiness",
        "cfaProgress": "cfa_progress",
    }


def test_active_tab_highlights_current_cfa_state() -> None:
    tb, evals = _toolbar("cfaReadiness")
    tb._update_active_cfa_tab()
    js = evals[-1]
    assert 'active="cfa_readiness"' in js
    # all native CFA ids are candidates so the others get cleared
    for tab in ("cfa_home", "cfa_study", "cfa_concept_map", "cfa_readiness"):
        assert tab in js
    assert "classList.add('is-active')" in js
    assert "setAttribute('aria-current','page')" in js
    assert "classList.remove('is-active')" in js


def test_non_cfa_state_clears_all_highlights() -> None:
    # On the deck list / a study session no CFA tab should read as active, so
    # `active` is null and every candidate tab has its highlight removed.
    tb, evals = _toolbar("deckBrowser")
    tb._update_active_cfa_tab()
    assert "active=null" in evals[-1]


def test_state_did_change_updates_highlight() -> None:
    tb, evals = _toolbar("cfaHome")
    tb._on_state_did_change("cfaConceptMap", "cfaHome")
    assert 'active="cfa_concept_map"' in evals[-1]
    # a transition into a non-CFA state clears it
    tb._on_state_did_change("review", "cfaConceptMap")
    assert "active=null" in evals[-1]


def test_redraw_refreshes_the_active_tab() -> None:
    calls: list[str] = []
    web = SimpleNamespace(eval=lambda js: calls.append("eval"))
    web.requiresCol = None
    mw = SimpleNamespace(
        state="cfaHome",
        media_syncer=SimpleNamespace(is_syncing=lambda: False),
    )
    tb = toolbar.Toolbar(mw, web)  # type: ignore[arg-type]
    # stub the sync-status side effects so redraw() exercises only the tab path
    tb.set_sync_active = lambda *a: None  # type: ignore[method-assign]
    tb.update_sync_status = lambda *a: None  # type: ignore[method-assign]
    called: list[bool] = []
    orig = tb._update_active_cfa_tab
    tb._update_active_cfa_tab = lambda: called.append(True) or orig()  # type: ignore[method-assign]
    tb.redraw()
    assert called == [True]


def test_chrome_styles_the_active_pill() -> None:
    src = (_REPO / "qt" / "aqt" / "cfa_chrome.py").read_text(encoding="utf-8")
    # a distinct active-tab treatment exists (filled accent pill on the accent
    # colour), not just the hover state
    assert ".hitem.is-active" in src
    assert 'background: {t["accent"]}' in src


def test_toolbar_registers_a_state_change_hook() -> None:
    src = (_REPO / "qt" / "aqt" / "toolbar.py").read_text(encoding="utf-8")
    assert "gui_hooks.state_did_change.append(self._on_state_did_change)" in src
