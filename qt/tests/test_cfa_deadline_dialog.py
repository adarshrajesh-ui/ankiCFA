# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""item5 / MEDIUM #8 — the desktop "Peak-on-Exam-Day" (DeadlineDialog) behaviour.

The DeadlineDialog is now a thin *host* for the shared ``ts/lib/cfa`` SvelteKit
page (``cfa-deadline/<deckId>``): the exam-date picker and the weakest-first
ranking moved out of the Qt body and into the web view + the
``mediasrv._cfa_deadline_payload`` handler. Under ``ANKI_TEST_MODE`` there is no
running mediasrv (``aqt.mw`` is ``None``), so constructing the dialog stubs the
``AnkiWebView`` — the dialog logic under test is the deck scoping + the payload,
not QtWebEngine.

Two defects stay covered, now asserted against the REAL payload the page renders
(the exact data the old Qt body computed):

* 5B — a fresh profile whose cards are all NEW must NOT dead-end on "No due cards
  to rank yet": the payload ranks new cards (recall 0.0, weakest first) via
  ``anki.cfa.deadline_retention_with_new`` and reports ``headerMode == "ranked"``.
* 5A — an absurd/far-future persisted exam date is self-healed back to the
  canonical default (``_sanitized_exam_date``) instead of being trusted verbatim;
  a sane date is left untouched.

Plus a host-level check that the dialog constructs and points its web view at the
current deck's ``cfa-deadline/<deckId>`` page.
"""

from __future__ import annotations

import os
import tempfile
from datetime import date, timedelta

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QWidget

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


class _StubWeb(QWidget):
    """Lightweight stand-in for ``AnkiWebView`` — records the SvelteKit path.

    The real web view needs a running mediasrv (``aqt.mw.serverURL()``), which
    does not exist under ``ANKI_TEST_MODE``; the dialog only needs *something*
    widget-shaped that exposes ``load_sveltekit_page`` + ``cleanup``.
    """

    last_path: str | None = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__()
        self.loaded_path: str | None = None

    def load_sveltekit_page(self, path: str) -> None:
        self.loaded_path = path
        _StubWeb.last_path = path

    def cleanup(self) -> None:
        pass


def _stub_webview(monkeypatch) -> None:
    _StubWeb.last_path = None
    monkeypatch.setattr(cfa, "AnkiWebView", _StubWeb)


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


def _deadline_payload(col: Collection, deck: DeckId) -> dict:
    """The REAL payload the SvelteKit deadline page renders for ``deck``."""
    from aqt import mediasrv

    return mediasrv._cfa_deadline_payload(col, int(deck))


# --- host: the dialog constructs and scopes the page to the current deck -----


def test_dialog_hosts_deadline_page_for_current_deck(monkeypatch) -> None:
    _stub_webview(monkeypatch)
    col = _empty_col()
    deck = _add_new_cards(col, "CFA", 3)
    col.decks.set_current(deck)

    mw = _StandInMW(col)
    dlg = cfa.DeadlineDialog(mw)  # type: ignore[arg-type]
    assert isinstance(dlg.web, _StubWeb)
    # The dialog scopes the SvelteKit page to the current deck, unchanged.
    assert dlg.web.loaded_path == f"cfa-deadline/{int(deck)}"
    dlg.reject()
    col.close()


# --- 5B: new cards are ranked, and the header is honest about it -------------


def test_payload_ranks_new_cards_on_fresh_all_new_deck() -> None:
    col = _empty_col()
    deck = _add_new_cards(col, "CFA", 5)
    col.decks.set_current(deck)
    assert len(col.find_cards("deck:CFA is:new")) == 5
    assert len(col.find_cards("deck:CFA is:due")) == 0

    payload = _deadline_payload(col, deck)
    # A fresh all-new deck must NOT dead-end empty: all five new cards are ranked.
    assert payload["cardCount"] == 5, "fresh all-new deck must not dead-end empty"
    assert payload["headerMode"] == "ranked"
    # New (unstudied) cards are treated as maximally weak: recall 0.0, on top.
    assert all(row["predictedRecall"] == 0.0 for row in payload["rows"])
    col.close()


def test_payload_empty_state_only_when_truly_empty() -> None:
    # The honest empty state still appears when the deck genuinely has no cards.
    col = _empty_col()
    deck = col.decks.id("CFA")  # created, but no cards added
    col.decks.set_current(deck)

    payload = _deadline_payload(col, deck)
    assert payload["cardCount"] == 0
    assert payload["headerMode"] == "empty"
    assert payload["rows"] == []
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


def test_payload_self_heals_absurd_persisted_date() -> None:
    col = _empty_col()
    deck = _add_new_cards(col, "CFA", 2)
    col.decks.set_current(deck)
    # Runtime pollution: a far-future date persisted in the synced config.
    anki_cfa.set_exam_config(col, exam_date="2099-12-31", topic_weights={})

    payload = _deadline_payload(col, deck)
    assert payload["examDate"] != "2099-12-31", "absurd persisted date must not be trusted"
    assert payload["examDate"] == cfa._default_exam_date(), "healed to the canonical default"
    col.close()


def test_payload_keeps_sane_persisted_date() -> None:
    col = _empty_col()
    deck = _add_new_cards(col, "CFA", 2)
    col.decks.set_current(deck)
    # A sane near-future date (30 days out) must survive untouched.
    sane = (date.today() + timedelta(days=30)).isoformat()
    anki_cfa.set_exam_config(col, exam_date=sane, topic_weights={})

    payload = _deadline_payload(col, deck)
    assert payload["examDate"] == sane, "a sane persisted exam date is left untouched"
    col.close()
