# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""item5 / MEDIUM #8 — the desktop "Peak-on-Exam-Day" (DeadlineDialog) fixes.

Two defects, both driven here against the real ``aqt.cfa.DeadlineDialog`` on an
offscreen Qt:

* 5B — a fresh profile whose cards are all NEW used to dead-end on "No due cards
  to rank yet" because the ranking excluded new cards. The dialog now ranks new
  cards (recall 0.0, weakest first) via ``anki.cfa.deadline_retention_with_new``
  and its header honestly says so.
* 5A — an absurd/far-future persisted exam date is self-healed back to the
  canonical default instead of being trusted verbatim; a sane date is untouched.
"""

from __future__ import annotations

import os
import tempfile
from datetime import date, timedelta

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLabel, QTableWidget, QWidget

from anki import cfa as anki_cfa
from anki.collection import Collection
from anki.decks import DeckId
from aqt import cfa

_APP: QApplication | None = None


def _app() -> QApplication:
    global _APP
    _APP = QApplication.instance() or QApplication(["test"])  # type: ignore[assignment]
    return _APP  # type: ignore[return-value]


def _empty_col() -> Collection:
    fd, path = tempfile.mkstemp(suffix=".anki2")
    os.close(fd)
    os.unlink(path)
    return Collection(path)


class _StandInMW(QWidget):
    def __init__(self, col: Collection) -> None:
        _app()
        super().__init__()
        self.col = col


def _add_new_cards(col: Collection, deck_name: str, n: int) -> DeckId:
    """Add ``n`` brand-new (never-reviewed) cards to ``deck_name``; return did."""
    nt = col.models.by_name("Basic")
    deck = col.decks.id(deck_name)
    for i in range(n):
        note = col.new_note(nt)
        note["Front"] = f"q{i}"
        note["Back"] = "a"
        note.tags = ["los::ethics"]
        col.add_note(note, deck)
    return deck


# --- 5B: new cards are ranked, and the header is honest about it -------------


def test_dialog_ranks_new_cards_on_fresh_all_new_deck() -> None:
    col = _empty_col()
    deck = _add_new_cards(col, "CFA", 5)
    col.decks.set_current(deck)
    assert len(col.find_cards("deck:CFA is:new")) == 5
    assert len(col.find_cards("deck:CFA is:due")) == 0

    mw = _StandInMW(col)
    dlg = cfa.DeadlineDialog(mw)  # type: ignore[arg-type]
    table = dlg.findChild(QTableWidget)
    assert table is not None
    assert table.rowCount() == 5, "fresh all-new deck must not dead-end empty"

    text = " ".join(lbl.text() for lbl in dlg.findChildren(QLabel))
    # The header honestly discloses that new cards are counted as weakest.
    assert "recall 0.0" in text
    assert "unstudied" in text.lower()
    assert "No cards to rank yet" not in text
    dlg.close()
    col.close()


def test_dialog_empty_state_only_when_truly_empty() -> None:
    # The honest empty state still appears when the deck genuinely has no cards.
    col = _empty_col()
    deck = col.decks.id("CFA")  # created, but no cards added
    col.decks.set_current(deck)

    mw = _StandInMW(col)
    dlg = cfa.DeadlineDialog(mw)  # type: ignore[arg-type]
    table = dlg.findChild(QTableWidget)
    assert table is not None
    assert table.rowCount() == 0

    text = " ".join(lbl.text() for lbl in dlg.findChildren(QLabel))
    assert "No cards to rank yet" in text
    assert "new cards first" in text.lower(), "empty hint stays honest about order"
    dlg.close()
    col.close()


# --- 5A: self-heal an absurd persisted exam date -----------------------------


def test_sanitized_exam_date_pure() -> None:
    today = date(2026, 7, 3)
    default = cfa._default_exam_date()

    # Absurd far-future -> healed to the canonical default.
    assert cfa._sanitized_exam_date("2028-08-23", today=today) == default
    assert cfa._sanitized_exam_date("2099-12-31", today=today) == default
    # Unparseable / missing -> healed.
    assert cfa._sanitized_exam_date("not-a-date", today=today) == default
    assert cfa._sanitized_exam_date(None, today=today) == default
    assert cfa._sanitized_exam_date("", today=today) == default
    # A sane near-future date is returned UNTOUCHED.
    sane = (today + timedelta(days=45)).isoformat()
    assert cfa._sanitized_exam_date(sane, today=today) == sane
    # The canonical default itself is within the horizon -> untouched.
    assert cfa._sanitized_exam_date(default, today=today) == default
    # A date exactly at the horizon boundary is kept; one past it is healed.
    at_edge = (today + timedelta(days=cfa._MAX_EXAM_HORIZON_DAYS)).isoformat()
    beyond = (today + timedelta(days=cfa._MAX_EXAM_HORIZON_DAYS + 1)).isoformat()
    assert cfa._sanitized_exam_date(at_edge, today=today) == at_edge
    assert cfa._sanitized_exam_date(beyond, today=today) == default


def test_dialog_self_heals_absurd_persisted_date() -> None:
    col = _empty_col()
    deck = _add_new_cards(col, "CFA", 2)
    col.decks.set_current(deck)
    # Runtime pollution: a far-future date persisted in the synced config.
    anki_cfa.set_exam_config(col, exam_date="2099-12-31", topic_weights={})

    mw = _StandInMW(col)
    dlg = cfa.DeadlineDialog(mw)  # type: ignore[arg-type]
    shown = dlg.date_edit.date().toString("yyyy-MM-dd")
    assert shown != "2099-12-31", "absurd persisted date must not be trusted"
    assert shown == cfa._default_exam_date(), "healed to the canonical default"
    dlg.close()
    col.close()


def test_dialog_keeps_sane_persisted_date() -> None:
    col = _empty_col()
    deck = _add_new_cards(col, "CFA", 2)
    col.decks.set_current(deck)
    # A sane near-future date (30 days out) must survive untouched.
    sane = (date.today() + timedelta(days=30)).isoformat()
    anki_cfa.set_exam_config(col, exam_date=sane, topic_weights={})

    mw = _StandInMW(col)
    dlg = cfa.DeadlineDialog(mw)  # type: ignore[arg-type]
    shown = dlg.date_edit.date().toString("yyyy-MM-dd")
    assert shown == sane, "a sane persisted exam date is left untouched"
    dlg.close()
    col.close()
