# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA Study — the deck-first Study workspace."""

# pylint: disable=import-error,broad-exception-caught

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import aqt
from anki.decks import DeckId
from anki.models import NotetypeId
from aqt.addcards import AddCards
from aqt.cfa_seed import ensure_cfa_study_decks
from aqt.sound import av_player
from aqt.utils import tooltip

if TYPE_CHECKING:
    from aqt.main import AnkiQt

ETHICS_DECK_NAME = "CFA::Ethics Pairs"
BASIC_NOTETYPE_NAME = "Basic"


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
        elif cmd == "cfa" and arg == "home":
            self.mw.moveToState("cfaHome")
        elif cmd == "cfa" and arg == "study":
            self.mw.moveToState("cfaStudy")
        elif cmd == "cfa" and arg == "readiness":
            self.mw.moveToState("cfaReadiness")
        elif cmd == "cfa" and arg == "progress":
            self.mw.moveToState("cfaProgress")
        elif cmd == "cfa" and arg == "sync":
            from aqt.cfa_home import trigger_cfa_sync

            trigger_cfa_sync(self.mw)
        elif cmd == "cfa" and arg == "sync-settings":
            from aqt.cfa_home import open_sync_settings

            open_sync_settings(self.mw)
        elif cmd in {"create", "create-cfa"}:
            self._create_cfa_deck()
        elif cmd == "import":
            self._import_notes()
        elif cmd == "study":
            self._study_deck(arg)
        elif cmd == "add":
            self._add_cards(arg)
        return False

    def _create_cfa_deck(self) -> None:
        deck_id = self._ensure_default_cfa_deck()
        if deck_id is None:
            tooltip("CFA deck sources are not available in this build.", parent=self.mw)
            return

        self.mw.col.decks.select(deck_id)
        self._reset_collection()
        self.mw.moveToState("cfaStudy")
        tooltip("CFA/Ethics study deck is ready.", parent=self.mw)

    def _study_deck(self, raw_deck_id: str) -> None:
        deck_id = self._deck_id_from_arg(raw_deck_id)
        if deck_id is None:
            return

        try:
            self.mw.col.decks.select(deck_id)
        except Exception:
            tooltip("That deck is no longer available.", parent=self.mw)
            return

        self._clear_cfa_review_marker()
        self._reset_collection()
        if not self._deck_has_cards_ready(deck_id):
            tooltip(
                "No cards are ready in this deck. Add cards or import CFA notes.",
                parent=self.mw,
            )
            self.mw.moveToState("cfaStudy")
            return

        self._mark_cfa_review(deck_id)
        self.mw.col.startTimebox()
        self.mw.moveToState("review")

    def _add_cards(self, raw_deck_id: str) -> None:
        deck_id = self._deck_id_from_arg(raw_deck_id)
        if deck_id is None and not raw_deck_id:
            deck_id = self._ensure_default_cfa_deck()

        try:
            add_cards = cast(AddCards, aqt.dialogs.open("AddCards", self.mw))
        except Exception:
            tooltip(
                "Use Anki's native Add Cards screen to add CFA cards on this device.",
                parent=self.mw,
            )
            return
        if deck_id is not None:
            add_cards.set_deck(deck_id)
        self._select_basic_note_type(add_cards)

    def _import_notes(self) -> None:
        on_import = getattr(self.mw, "onImport", None)
        if callable(on_import):
            on_import()
            return
        tooltip(
            "Use Anki's native Import action to bring CFA notes onto this device.",
            parent=self.mw,
        )

    def _ensure_default_cfa_deck(self) -> DeckId | None:
        if not self.mw.col:
            return None

        ensure_cfa_study_decks(self.mw.col)
        deck_id = self.mw.col.decks.id_for_name(ETHICS_DECK_NAME)
        return DeckId(int(deck_id)) if deck_id is not None else None

    def _select_basic_note_type(self, add_cards: AddCards) -> None:
        col = self.mw.col
        if not col:
            return

        notetype = col.models.by_name(BASIC_NOTETYPE_NAME)
        if not notetype:
            return

        try:
            add_cards.set_note_type(NotetypeId(notetype["id"]))
        except Exception:
            # Add Cards is already open and deck-selected; failing to switch the
            # optional note type should not make the Study button feel broken.
            return

    def _deck_id_from_arg(self, raw_deck_id: str) -> DeckId | None:
        if not raw_deck_id:
            return None
        try:
            parsed = int(raw_deck_id)
        except ValueError:
            tooltip("That deck link is no longer valid.", parent=self.mw)
            return None
        if parsed <= 0:
            tooltip("That deck link is no longer valid.", parent=self.mw)
            return None
        return DeckId(parsed)

    def _reset_collection(self) -> None:
        if hasattr(self.mw, "reset"):
            self.mw.reset()

    def _mark_cfa_review(self, deck_id: DeckId) -> None:
        """Mark the next review as launched from the CFA Study deck cards."""
        try:
            from aqt.cfa_chrome import register as register_cfa_chrome

            register_cfa_chrome()
        except Exception:
            # Study must still enter Anki's reviewer if chrome registration is
            # already unavailable for an unrelated startup/import issue.
            pass
        setattr(self.mw, "_cfa_review_from_study", True)
        setattr(self.mw, "_cfa_review_deck_id", int(deck_id))

    def _clear_cfa_review_marker(self) -> None:
        setattr(self.mw, "_cfa_review_from_study", False)
        setattr(self.mw, "_cfa_review_deck_id", None)

    def _deck_has_cards_ready(self, deck_id: DeckId) -> bool:
        """True when the selected deck has scheduler queues ready right now."""
        try:
            row = self._find_due_tree_row(self.mw.col.sched.deck_due_tree(), deck_id)
            if row is not None:
                return (
                    int(row.new_count) + int(row.learn_count) + int(row.review_count)
                ) > 0
        except Exception:
            pass

        try:
            return bool(self.mw.col.decks.card_count(deck_id, include_subdecks=True))
        except Exception:
            return False

    def _find_due_tree_row(self, node: Any, deck_id: DeckId) -> Any | None:
        if int(getattr(node, "deck_id", 0)) == int(deck_id):
            return node
        for child in getattr(node, "children", []):
            if match := self._find_due_tree_row(child, deck_id):
                return match
        return None
