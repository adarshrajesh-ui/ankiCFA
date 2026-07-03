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
from aqt.cfa_seed import ensure_ethics_deck, ensure_ethics_passages_deck

ETHICS_DECK = "CFA::Ethics Pairs"
PASSAGES_DECK = "CFA::Ethics Passages"

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
        assert "No cards to rank yet" in dlg._header.text()
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


# ---------------------------------------------------------------------------
# item2 (P1 fix): "Study by Exam Priority" never dead-ends on a FRESH profile.
#
# Regression guard for the fresh-profile dead-end: the first-launch seeder
# creates the CFA decks but never SELECTS one, so the current deck stays the
# empty built-in "Default" deck. "Study by Exam Priority" scoped the exam queue
# to that current deck, so `build_exam_queue` returned 0 card_ids and the action
# dead-ended with the "no studyable cards" modal — even though hundreds of NEW
# CFA cards (treated as maximally weak, R=0) were waiting in the CFA decks. The
# fix widens the scope to the whole collection when the current deck has nothing
# studyable, so the NEW cards are reached and review is entered. This test FAILS
# without the fix (dead-end modal, never enters review) and PASSES with it.
# ---------------------------------------------------------------------------


def test_study_by_exam_priority_from_empty_default_deck_no_dead_end(
    monkeypatch,
) -> None:
    col = _empty_col()
    mw = _StandInMW(col)
    try:
        # 30 NEW ethics cards live in CFA::Ethics Pairs, a sibling of Default.
        added = ensure_ethics_deck(col)
        assert added == 30
        anki_cfa.set_exam_config(
            col, exam_date="2026-08-25", topic_weights={"los::ethics": 1.0}
        )

        # Reproduce the fresh-profile precondition EXACTLY: do NOT select a CFA
        # deck. The current deck is the empty built-in "Default" deck.
        cur = col.decks.get_current_id()
        assert col.decks.name(cur) == "Default"
        assert len(col.find_cards('deck:"Default" is:new')) == 0

        tips: list[str] = []
        monkeypatch.setattr(cfa, "tooltip", lambda *a, **k: tips.append(a[0]))
        monkeypatch.setattr(
            cfa, "showInfo", lambda *a, **k: tips.append("INFO:" + a[0])
        )

        cfa.study_by_exam_priority(mw)  # type: ignore[arg-type]

        # Must NOT dead-end: the widened scope reaches the 30 NEW cards and
        # enters review, reporting the new count honestly.
        assert "review" in mw.states, f"exam-priority dead-ended: {tips}"
        assert not any(t.startswith("INFO:") for t in tips), (
            f"dead-end modal fired: {tips}"
        )
        assert tips, "expected an honest exam-priority tooltip"
        msg = tips[0]
        assert "30" in msg and "new" in msg.lower(), msg

        # The filtered study deck was actually populated with the 30 new cards.
        prio = col.decks.id_for_name(cfa.EXAM_PRIORITY_DECK_NAME)
        assert prio is not None
        assert col.decks.card_count(prio, include_subdecks=False) == 30
    finally:
        col.close()


# The collection-wide fallback is gated to the built-in "Default" deck so it
# only bootstraps a fresh profile. A user who deliberately selected a specific
# (non-Default) deck and then finished/emptied it must be told THAT deck is
# done, not silently hijacked into a queue spanning unrelated decks.


def test_study_by_exam_priority_non_default_empty_deck_does_not_hijack(
    monkeypatch,
) -> None:
    col = _empty_col()
    mw = _StandInMW(col)
    try:
        # 30 studyable NEW cards live in CFA::Ethics Pairs.
        added = ensure_ethics_deck(col)
        assert added == 30
        anki_cfa.set_exam_config(
            col, exam_date="2026-08-25", topic_weights={"los::ethics": 1.0}
        )

        # Select a DIFFERENT, non-Default deck that has nothing studyable.
        empty_did = col.decks.id("CFA::Finished")
        assert empty_did is not None
        col.decks.set_current(empty_did)
        cur = col.decks.get_current_id()
        assert col.decks.name(cur) != "Default"
        assert col.decks.card_count(cur, include_subdecks=True) == 0

        tips: list[str] = []
        monkeypatch.setattr(cfa, "tooltip", lambda *a, **k: tips.append(a[0]))
        monkeypatch.setattr(
            cfa, "showInfo", lambda *a, **k: tips.append("INFO:" + a[0])
        )

        cfa.study_by_exam_priority(mw)  # type: ignore[arg-type]

        # Must NOT enter review on the unrelated CFA::Ethics Pairs cards, and
        # must surface a deck-scoped "this deck is done" modal instead.
        assert "review" not in mw.states, f"exam-priority hijacked: {tips}"
        assert any(t.startswith("INFO:") for t in tips), (
            f"expected deck-scoped modal, got: {tips}"
        )
        assert col.decks.id_for_name(cfa.EXAM_PRIORITY_DECK_NAME) is None
    finally:
        col.close()


# ---------------------------------------------------------------------------
# item4 (P1 fix): the F1 one-passage flagship "CFA::Ethics Passages" is
# REACHABLE on desktop via a dedicated "Study Ethics (One-Passage)" action.
#
# Root cause: the passages deck is intentionally NOT part of the first-launch
# seeder (it is a sibling of the minimal-pairs deck), and it had NO desktop
# CFA-menu entry, so it was unreachable on desktop. The new action seeds it on
# demand (idempotently) and enters review on it as a NORMAL (non-filtered) deck:
# seed-if-missing -> select the deck -> move Anki into review. It is re-entrant
# (a repeat invocation neither errors nor duplicates the deck/cards) and never
# shows the false "not available in this build" modal when the deck exists.
# These tests FAIL without the fix (ensure_ethics_passages_deck /
# study_ethics_passages do not exist) and PASS with it.
# ---------------------------------------------------------------------------


def test_ensure_ethics_passages_deck_seeds_then_idempotent() -> None:
    col = _empty_col()
    try:
        assert _card_count(col, PASSAGES_DECK) == 0

        added = ensure_ethics_passages_deck(col)
        assert added == 30, f"expected the 30 shipped passages, got {added}"
        assert _card_count(col, PASSAGES_DECK) == 30

        # Second call is a no-op — never re-imports or clobbers.
        again = ensure_ethics_passages_deck(col)
        assert again == 0
        assert _card_count(col, PASSAGES_DECK) == 30
    finally:
        col.close()


def test_study_ethics_passages_seeds_on_demand_and_enters_review(monkeypatch) -> None:
    col = _empty_col()
    mw = _StandInMW(col)
    try:
        info_calls: list[str] = []
        warn_calls: list[str] = []
        monkeypatch.setattr(cfa, "showInfo", lambda *a, **k: info_calls.append(a[0]))
        monkeypatch.setattr(cfa, "showWarning", lambda *a, **k: warn_calls.append(a[0]))
        monkeypatch.setattr(cfa, "tooltip", lambda *a, **k: None)

        # The passages deck does not exist on a fresh profile (not seeded at
        # first launch) — the exact precondition that made it unreachable.
        assert _card_count(col, PASSAGES_DECK) == 0
        cfa.study_ethics_passages(mw)  # type: ignore[arg-type]

        # The 30 passages were preloaded on demand, the deck was selected, and
        # we entered the reviewer — no dead-end, no false modal.
        assert _card_count(col, PASSAGES_DECK) == 30
        assert "review" in mw.states
        assert col.decks.name(col.decks.get_current_id()) == PASSAGES_DECK
        assert info_calls == [], f"unexpected dead-end dialog: {info_calls}"
        assert warn_calls == [], f"unexpected warning: {warn_calls}"
    finally:
        col.close()


def test_study_ethics_passages_is_reentrant_no_false_modal(monkeypatch) -> None:
    col = _empty_col()
    mw = _StandInMW(col)
    try:
        info_calls: list[str] = []
        warn_calls: list[str] = []
        monkeypatch.setattr(cfa, "showInfo", lambda *a, **k: info_calls.append(a[0]))
        monkeypatch.setattr(cfa, "showWarning", lambda *a, **k: warn_calls.append(a[0]))
        monkeypatch.setattr(cfa, "tooltip", lambda *a, **k: None)

        # First invocation seeds the 30 passages and enters review.
        cfa.study_ethics_passages(mw)  # type: ignore[arg-type]
        assert mw.states.count("review") == 1
        assert _card_count(col, PASSAGES_DECK) == 30

        # Second invocation is the re-entrancy case: it must RE-ENTER review with
        # the SAME 30 cards — no duplication, no error, and (critically) NO false
        # "not available in this build" modal now that the deck demonstrably
        # exists with cards.
        cfa.study_ethics_passages(mw)  # type: ignore[arg-type]
        assert mw.states.count("review") == 2, (
            "repeat invocation must re-enter the reviewer"
        )
        assert _card_count(col, PASSAGES_DECK) == 30, (
            "repeat invocation must not duplicate the deck or its cards"
        )
        assert info_calls == [], f"false dead-end modal fired: {info_calls}"
        assert warn_calls == [], f"unexpected warning: {warn_calls}"
    finally:
        col.close()
