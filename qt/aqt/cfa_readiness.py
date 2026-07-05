# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA Exam Readiness — the native in-window "readiness report" tab.

Renders the SvelteKit ``cfa-readiness/{deck_id}`` page (the Bayesian pass/fail
hero, the three give-up-gated honest-score bands, the per-topic recall table)
into the MAIN webview, scoped to the current deck. It is built from the SAME
``anki.cfa`` data the old modal ``ExamReadinessDialog`` embedded, so the report
is byte-for-byte the same — only its container changed.

Historically Readiness opened as a modal ``QDialog`` while Home / Study /
Concept Map were first-class main-window states, so the top-bar "Readiness" tab
read as a bolted-on Anki popup rather than a native CFA screen. This controller
mirrors :class:`aqt.cfa_concept_map.CfaConceptMap` so Readiness plugs into the
main-window state machine as the ``cfaReadiness`` state; the CFA-branded top bar
(Home / Study / Ethics / Concept Map / Readiness) is redrawn on show, so the
user is never trapped — Home is always one click away.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aqt.sound import av_player
from aqt.utils import openLink

if TYPE_CHECKING:
    from aqt.main import AnkiQt


class CfaReadiness:
    """Controller for the CFA Exam Readiness state."""

    def __init__(self, mw: AnkiQt) -> None:
        self.mw = mw
        self.web = mw.web

    def show(self) -> None:
        av_player.stop_and_clear_queue()
        self.web.set_bridge_command(self._link_handler, self)
        # redraw the (CFA-branded) top bar, matching CfaHome/CfaConceptMap
        self.mw.toolbar.redraw()
        deck_id = self.mw.col.decks.get_current_id()
        self.web.load_sveltekit_page(f"cfa-readiness/{int(deck_id)}")
        self.web.setFocus()

    # Bridge (pycmd / bridgeCommand) handlers
    ##########################################################################

    def _link_handler(self, url: str) -> bool:
        # The readiness report is self-contained, but any CTA it grows delegates
        # to the existing CFA entry points so this screen adds no new
        # study/scoring logic of its own.
        import aqt.cfa as cfa

        mw = self.mw
        if url == "cfa:priority":
            cfa.study_by_exam_priority(mw)
        elif url == "cfa:ethics":
            cfa.study_ethics_pairs(mw)
        elif url == "cfa:deadline":
            cfa.show_deadline(mw)
        elif url == "cfa:conceptmap":
            mw.moveToState("cfaConceptMap")
        elif url == "cfa:home":
            mw.moveToState("cfaHome")
        elif url == "cfa:decks":
            mw.moveToState("deckBrowser")
        elif url.lower().startswith("http"):
            openLink(url)
        return False
