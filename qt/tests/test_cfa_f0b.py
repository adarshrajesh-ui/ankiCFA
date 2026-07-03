# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""F0b — Visible desktop fixes (demoable on a fresh profile).

Covers the four fixes that make the CFA desktop UI honest and dead-end-free on
a brand new collection:

1. On-demand ethics preload: ``ensure_ethics_deck`` seeds the 30 shipped pairs
   idempotently.
2. No dead-end: ``study_ethics_pairs`` seeds on demand and enters review instead
   of pointing at a non-existent menu item.
3. Peak-on-Exam-Day exam-date picker: the dialog defaults sensibly with NO due
   cards, and its picker persists the chosen date via ``set_exam_config``.
4. Study-by-Exam-Priority includes NEW cards and says so honestly.

Runs against a real ``anki.collection.Collection`` with a lightweight QWidget
stand-in for the main window (offscreen Qt), so no full AnkiQt/profile needed.
"""

from __future__ import annotations

import os
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QWidget

from anki import cfa as anki_cfa
from anki.collection import Collection
from aqt import cfa
from aqt.cfa_seed import ensure_ethics_deck

ETHICS_DECK = "CFA::Ethics Pairs"

# Hold a module-level reference so the QApplication is not garbage-collected.
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
    """Minimal stand-in for AnkiQt: a real QWidget carrying a live collection.

    Records the study-state transition so tests can assert we actually entered
    review rather than hitting a dead-end.
    """

    def __init__(self, col: Collection) -> None:
        _app()
        super().__init__()
        self.col = col
        self.states: list[str] = []

    def reset(self) -> None:  # noqa: D401 - AnkiQt API shim
        pass

    def moveToState(self, state: str) -> None:  # noqa: N802 - AnkiQt API name
        self.states.append(state)


def _card_count(col: Collection, name: str) -> int:
    did = col.decks.id_for_name(name)
    return col.decks.card_count(did, include_subdecks=True) if did is not None else 0


# ---------------------------------------------------------------------------
# Fix 1: on-demand ethics preload is idempotent
# ---------------------------------------------------------------------------


def test_ensure_ethics_deck_seeds_then_idempotent() -> None:
    col = _empty_col()
    try:
        assert _card_count(col, ETHICS_DECK) == 0

        added = ensure_ethics_deck(col)
        assert added == 30, f"expected the 30 shipped pairs, got {added}"
        assert _card_count(col, ETHICS_DECK) == 30

        # Second call is a no-op — never re-imports or clobbers.
        again = ensure_ethics_deck(col)
        assert again == 0
        assert _card_count(col, ETHICS_DECK) == 30
    finally:
        col.close()


# ---------------------------------------------------------------------------
# Fix 2: study_ethics_pairs self-heals instead of dead-ending
# ---------------------------------------------------------------------------


def test_study_ethics_pairs_seeds_on_demand_and_enters_review(monkeypatch) -> None:
    col = _empty_col()
    mw = _StandInMW(col)
    try:
        info_calls: list[str] = []
        monkeypatch.setattr(cfa, "showInfo", lambda *a, **k: info_calls.append(a[0]))
        monkeypatch.setattr(cfa, "tooltip", lambda *a, **k: None)

        assert _card_count(col, ETHICS_DECK) == 0
        cfa.study_ethics_pairs(mw)  # type: ignore[arg-type]

        # The 30 pairs were preloaded on demand and we entered the reviewer —
        # no "import first" dead-end.
        assert _card_count(col, ETHICS_DECK) == 30
        assert "review" in mw.states
        assert info_calls == [], f"unexpected dead-end dialog: {info_calls}"
    finally:
        col.close()


# ---------------------------------------------------------------------------
# item1 (P1 fix): "Study Ethics Minimal-Pairs" is RE-ENTRANT.
#
# Regression guard for the dead-end where a repeat invocation created a fresh,
# name-colliding filtered deck. On the second call the previous build still held
# the 30 cards, and Anki won't gather cards already inside a filtered deck, so
# the rebuild gathered 0 → "No cards to study" tooltip → the retry-after-seed
# then surfaced a FALSE "CFA::Ethics Pairs deck is not available in this build"
# modal even though the 30 cards clearly exist. The fix reuses/rebuilds the
# existing same-named filtered deck (cards home → re-gather) so the action
# reliably re-enters review every time, and the false modal never fires when the
# cards exist. This test FAILS without the fix and PASSES with it.
# ---------------------------------------------------------------------------

STUDY_DECK = "CFA::Study — Ethics Minimal-Pairs"


def test_study_ethics_pairs_is_reentrant_no_false_modal(monkeypatch) -> None:
    col = _empty_col()
    mw = _StandInMW(col)
    try:
        info_calls: list[str] = []
        warn_calls: list[str] = []
        monkeypatch.setattr(cfa, "showInfo", lambda *a, **k: info_calls.append(a[0]))
        monkeypatch.setattr(cfa, "showWarning", lambda *a, **k: warn_calls.append(a[0]))
        monkeypatch.setattr(cfa, "tooltip", lambda *a, **k: None)

        # The 30 ethics cards exist up front (the exact precondition under which
        # the false "not available in this build" modal must never appear).
        assert ensure_ethics_deck(col) == 30
        assert _card_count(col, ETHICS_DECK) == 30

        # First invocation pulls the 30 cards into the filtered study deck.
        cfa.study_ethics_pairs(mw)  # type: ignore[arg-type]
        did1 = col.decks.id_for_name(STUDY_DECK)
        assert did1 is not None, "first invocation should build the study deck"
        assert col.decks.card_count(did1, include_subdecks=False) == 30
        assert mw.states.count("review") == 1

        # Second invocation is the bug: it must RE-ENTER review with the same 30
        # cards, not dead-end. Without the fix it gathers 0 and shows the false
        # "not available in this build" modal.
        cfa.study_ethics_pairs(mw)  # type: ignore[arg-type]

        # The false modal must NEVER fire when the cards demonstrably exist.
        assert info_calls == [], f"false dead-end modal fired: {info_calls}"
        assert warn_calls == [], f"unexpected warning: {warn_calls}"
        # And we must actually be back in the reviewer with the 30 cards.
        assert mw.states.count("review") == 2, (
            "repeat invocation must re-enter the reviewer"
        )
        did2 = col.decks.id_for_name(STUDY_DECK)
        assert did2 is not None, "repeat invocation must keep a populated deck"
        assert col.decks.card_count(did2, include_subdecks=False) == 30, (
            "repeat invocation must re-gather the 30 ethics cards, not 0"
        )
        # The 30 ethics cards are never lost from the source deck either.
        assert _card_count(col, ETHICS_DECK) == 30
    finally:
        col.close()


# ---------------------------------------------------------------------------
# Fix 3: Peak-on-Exam-Day date picker
# ---------------------------------------------------------------------------


def test_deadline_dialog_renders_without_due_cards() -> None:
    col = _empty_col()
    mw = _StandInMW(col)
    try:
        assert anki_cfa.get_exam_config(col) is None
        dlg = cfa.DeadlineDialog(mw)  # type: ignore[arg-type]

        # Defaults to the sensible CFA exam day even with no config and no cards.
        assert dlg.date_edit.date().toString("yyyy-MM-dd") == cfa._default_exam_date()
        # Renders cleanly (no crash) with an empty, honest table.
        assert dlg._table.rowCount() == 0
        assert "No due cards" in dlg._header.text()
    finally:
        col.close()


def test_deadline_dialog_apply_persists_exam_date(monkeypatch) -> None:
    col = _empty_col()
    mw = _StandInMW(col)
    try:
        monkeypatch.setattr(cfa, "tooltip", lambda *a, **k: None)
        dlg = cfa.DeadlineDialog(mw)  # type: ignore[arg-type]

        from aqt.qt import QDate

        dlg.date_edit.setDate(QDate(2027, 5, 15))
        dlg._apply_date()

        cfg = anki_cfa.get_exam_config(col)
        assert cfg is not None
        assert cfg["exam_date"] == "2027-05-15"
    finally:
        col.close()


# ---------------------------------------------------------------------------
# Fix 4: exam-priority queue includes NEW cards and reports it honestly
# ---------------------------------------------------------------------------


def test_study_by_exam_priority_includes_new_cards(monkeypatch) -> None:
    col = _empty_col()
    mw = _StandInMW(col)
    try:
        # Seed the ethics deck (all NEW cards) and configure a matching weight.
        added = ensure_ethics_deck(col)
        assert added == 30
        anki_cfa.set_exam_config(
            col, exam_date="2026-08-25", topic_weights={"los::ethics": 1.0}
        )
        did = col.decks.id_for_name(ETHICS_DECK)
        assert did is not None
        col.decks.select(did)

        tips: list[str] = []
        monkeypatch.setattr(cfa, "tooltip", lambda *a, **k: tips.append(a[0]))
        monkeypatch.setattr(
            cfa, "showInfo", lambda *a, **k: tips.append("INFO:" + a[0])
        )

        cfa.study_by_exam_priority(mw)  # type: ignore[arg-type]

        # A fresh deck is NOT empty — all 30 new cards entered the queue, and we
        # honestly report that they are new.
        assert "review" in mw.states
        assert tips, "expected an honest exam-priority tooltip"
        msg = tips[0]
        assert "30" in msg and "new" in msg.lower(), msg
    finally:
        col.close()
