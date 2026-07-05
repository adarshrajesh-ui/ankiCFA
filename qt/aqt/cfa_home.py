# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA Home — the native CFA landing dashboard.

This is the screen the app opens into instead of the stock Anki deck list. It
renders the SvelteKit ``cfa-home`` page (a three-honest-score snapshot + exam
countdown, built from the shared CFA design system) into the main webview and
routes the page's CTA bridge commands to the EXISTING CFA study/report entry
points in :mod:`aqt.cfa`.

It mirrors the ``DeckBrowser``/``Overview`` controller shape so it plugs into the
main-window state machine as the ``cfaHome`` state; ``moveToState('deckBrowser')``
(the "Decks" CTA and the ``d`` shortcut) always remains one click away.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aqt.sound import av_player
from aqt.utils import openLink, tooltip

if TYPE_CHECKING:
    from aqt.main import AnkiQt

# The canonical CFA study deck the Home dashboard reports on.
CFA_DECK_NAME = "CFA Level II"


class CfaHome:
    """Controller for the CFA Home landing state."""

    def __init__(self, mw: AnkiQt) -> None:
        self.mw = mw
        self.web = mw.web

    def show(self) -> None:
        av_player.stop_and_clear_queue()
        self.web.set_bridge_command(self._link_handler, self)
        # redraw the (CFA-branded) top bar, matching DeckBrowser/Overview
        self.mw.toolbar.redraw()
        self.web.load_sveltekit_page("cfa-home")
        self.web.setFocus()

    # Bridge (pycmd / bridgeCommand) handlers
    ##########################################################################

    def _link_handler(self, url: str) -> bool:
        # Every CTA delegates to an existing, self-healing CFA entry point so the
        # Home dashboard adds NO new study/scoring logic of its own.
        from aqt import cfa

        mw = self.mw
        if url == "cfa:ethics":
            cfa.study_ethics_pairs(mw)
        elif url == "cfa:priority":
            cfa.study_by_exam_priority(mw)
        elif url == "cfa:study":
            mw.moveToState("cfaStudy")
        elif url == "cfa:readiness":
            cfa.show_exam_readiness(mw)
        elif url == "cfa:conceptmap":
            mw.moveToState("cfaConceptMap")
        elif url == "cfa:home":
            mw.moveToState("cfaHome")
        elif url == "cfa:deadline":
            cfa.show_deadline(mw)
        elif url == "cfa:decks":
            mw.moveToState("deckBrowser")
        elif url == "cfa:ai":
            open_ai_settings(mw)
        elif url == "cfa:sync":
            trigger_cfa_sync(mw)
        elif url == "cfa:sync-settings":
            open_sync_settings(mw)
        elif url.lower().startswith("http"):
            openLink(url)
        return False

    def _study_cfa_deck(self) -> None:
        mw = self.mw
        did = mw.col.decks.id_for_name(CFA_DECK_NAME)
        if did is None:
            tooltip("The CFA Level II deck isn't set up yet.", parent=mw)
            return
        mw.col.decks.select(did)
        mw.moveToState("overview")


def open_ai_settings(mw: AnkiQt) -> None:
    """Open the in-app AI settings dialog (master + per-feature AI toggles)."""
    from aqt.cfa_ai_settings import open_ai_settings as _open

    _open(mw)


def open_sync_settings(mw: AnkiQt) -> None:
    """Open the in-app sync status/actions dialog."""
    from aqt.cfa_sync_connect import open_sync_settings as _open

    _open(mw)


def trigger_cfa_sync(mw: AnkiQt) -> None:
    """Connect if needed; otherwise run the existing normal GUI sync."""
    from aqt.cfa_sync_connect import connect_cfa_sync

    try:
        connected = mw.pm.sync_auth() is not None
    except Exception:
        connected = False
    if connected:
        mw.on_sync_button_clicked()
    else:
        connect_cfa_sync(mw)
