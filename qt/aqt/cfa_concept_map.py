# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA Concept Map — the radial "mastery map" tab.

Renders the SvelteKit ``cfa-concept-map`` page (CFA at the centre, the 10 test
sections orbiting it sized by exam weight, subsections beyond; fill goes
light-gray → turquoise by mastery) into the main webview. It reuses the SAME
per-topic payload the CFA Home dashboard is built from, so the map and the three
honest scores stay in lockstep.

Mirrors the :class:`aqt.cfa_home.CfaHome` controller shape so it plugs into the
main-window state machine as the ``cfaConceptMap`` state; the top-bar nav and the
``d`` Decks shortcut remain one click away.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aqt.sound import av_player
from aqt.utils import openLink

if TYPE_CHECKING:
    from aqt.main import AnkiQt


class CfaConceptMap:
    """Controller for the CFA Concept Map state."""

    def __init__(self, mw: AnkiQt) -> None:
        self.mw = mw
        self.web = mw.web

    def show(self) -> None:
        av_player.stop_and_clear_queue()
        self.web.set_bridge_command(self._link_handler, self)
        # redraw the (CFA-branded) top bar, matching CfaHome/DeckBrowser
        self.mw.toolbar.redraw()
        self.web.load_sveltekit_page("cfa-concept-map")
        self.web.setFocus()

    # Bridge (pycmd / bridgeCommand) handlers
    ##########################################################################

    def _link_handler(self, url: str) -> bool:
        # The map is self-contained (hover/click are handled client-side), but a
        # node's "next drill" chip can delegate to the existing CFA study entry
        # points so the map adds no new study/scoring logic of its own.
        from aqt import cfa

        mw = self.mw
        if url == "cfa:priority":
            cfa.study_by_exam_priority(mw)
        elif url == "cfa:ethics":
            cfa.study_ethics_pairs(mw)
        elif url == "cfa:study":
            mw.moveToState("cfaStudy")
        elif url == "cfa:conceptmap":
            mw.moveToState("cfaConceptMap")
        elif url == "cfa:readiness":
            cfa.show_exam_readiness(mw)
        elif url == "cfa:progress":
            mw.moveToState("cfaProgress")
        elif url == "cfa:sync":
            from aqt.cfa_home import trigger_cfa_sync

            trigger_cfa_sync(mw)
        elif url == "cfa:sync-settings":
            from aqt.cfa_home import open_sync_settings

            open_sync_settings(mw)
        elif url == "cfa:home":
            mw.moveToState("cfaHome")
        elif url == "cfa:decks":
            mw.moveToState("deckBrowser")
        elif url.lower().startswith("http"):
            openLink(url)
        return False
