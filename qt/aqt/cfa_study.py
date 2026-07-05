# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA Study — the deck-first Study workspace."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import aqt
from anki.decks import DeckId
from aqt.addcards import AddCards
from aqt.operations.deck import add_deck_dialog
from aqt.sound import av_player

if TYPE_CHECKING:
    from aqt.main import AnkiQt


class CfaStudy:
    """Controller for the CFA Study tab."""

    def __init__(self, mw: AnkiQt) -> None:
        self.mw = mw
        self.web = mw.web

    def show(self) -> None:
        av_player.stop_and_clear_queue()
        self.web.set_bridge_command(self._link_handler, self)
        self.mw.toolbar.redraw()
        self.web.load_sveltekit_page("cfa-study")
        self.web.setFocus()

    def _link_handler(self, url: str) -> bool:
        if ":" in url:
            cmd, arg = url.split(":", 1)
        else:
            cmd, arg = url, ""

        if cmd == "cfa" and arg == "conceptmap":
            self.mw.moveToState("cfaConceptMap")
        elif cmd == "cfa" and arg == "study":
            self.mw.moveToState("cfaStudy")
        elif cmd == "cfa" and arg == "readiness":
            self.mw.moveToState("cfaReadiness")
        elif cmd == "cfa" and arg == "sync":
            from aqt.cfa_home import trigger_cfa_sync

            trigger_cfa_sync(self.mw)
        elif cmd == "cfa" and arg == "sync-settings":
            from aqt.cfa_home import open_sync_settings

            open_sync_settings(self.mw)
        elif cmd in {"create", "create-cfa"}:
            self._create_deck()
        elif cmd == "import":
            self.mw.onImport()
        elif cmd == "study":
            self._study_deck(arg)
        elif cmd == "add":
            self._add_cards(arg)
        return False

    def _create_deck(self) -> None:
        if op := add_deck_dialog(
            parent=self.mw, default_text=self.mw.col.decks.current()["name"]
        ):
            op.run_in_background()

    def _study_deck(self, raw_deck_id: str) -> None:
        if raw_deck_id:
            self.mw.col.decks.select(DeckId(int(raw_deck_id)))
        self.mw.onOverview()

    def _add_cards(self, raw_deck_id: str) -> None:
        add_cards = cast(AddCards, aqt.dialogs.open("AddCards", self.mw))
        if raw_deck_id:
            add_cards.set_deck(DeckId(int(raw_deck_id)))
